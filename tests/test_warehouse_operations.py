"""Regressions for distributed station approaches, role selection and single-consumer web commands."""
import asyncio
from contextlib import closing, contextmanager
import json
from pathlib import Path
import signal
from tempfile import TemporaryDirectory
from uuid import uuid4

import httpx
import pytest
import yaml

from backend.dashboard.api import create_app
from backend.dashboard.publisher import publish_fleet
from backend.fleet_manager.builder import build_fleet_manager_from_config
from backend.fleet_manager.persistence.store import SQLiteStore
from backend.fleet_manager.event_loop import FleetEventLoop
from fleet_config import load_config
from fleet_config.loader import read_yaml
from fleet_config.occupancy import check_approaches, profile_digest, raster
from fleet_config.warehouse_assets import generate

PROFILE = Path('config/fleet.warehouse-30x18.yaml').resolve()
ORIGIN = 'http://127.0.0.1:19941'


def test_distributed_profile_clearance_capacity_and_old_profiles(tmp_path):
    config = load_config(PROFILE)
    w = config.warehouse
    assert (w.bounds.x_max-w.bounds.x_min, w.bounds.y_max-w.bounds.y_min, w.grid_m) == (30,18,.25)
    assert len(w.racks) == 10 and sum(rack.bays for rack in w.racks) == 58
    picks = [p for p in w.transfer_points if p.rack_id]
    assert len(picks) == 10 and {p.rack_id for p in picks} == {r.id for r in w.racks}
    assert len([a for a in w.aisles if a.role == 'main']) == 4
    assert len([a for a in w.aisles if a.role == 'cross']) == 3
    assert len(config.stations.charging_stations) == 6
    assert {p.id for p in w.transfer_points} >= {'pick_A1','pick_C2','pick_B1','inbound_1','delivery-01'}
    check_approaches(config, *raster(w))
    generate(PROFILE, tmp_path / 'generated')
    generated = json.loads((tmp_path/'generated/scene.json').read_text())
    assert generated == w.scene_payload()
    from xml.etree import ElementTree as ET

    world = ET.parse(tmp_path/'generated/warehouse.sdf')
    for robot in config.robots:
        sensors = world.findall(f".//model[@name='{robot.id}']/link/sensor[@type='contact']")
        assert len(sensors) == 5
        assert all(len(sensor.findall('contact/collision')) == 1 for sensor in sensors)
    for name, size in [('fleet.warehouse-grid.yaml',(20,12)), ('fleet.warehouse-grid-12x8.yaml',(12,8))]:
        old = load_config(PROFILE.with_name(name)).warehouse.bounds
        assert (old.x_max-old.x_min, old.y_max-old.y_min) == size


def test_blocked_approach_and_invalid_example_are_rejected(tmp_path):
    raw = read_yaml(PROFILE)
    for robot in raw['robots']:
        robot['nav2_params_path'] = str(PROFILE.parent / robot['nav2_params_path'])
    # A larger required physical envelope must fail even though its centre is on free floor.
    raw['warehouse']['approach_clearance_m'] = .8
    path = tmp_path/'profile.yaml'
    path.write_text(yaml.safe_dump(raw,allow_unicode=True))
    with pytest.raises(ValueError,match='approach footprint is blocked'):
        load_config(path)
    raw = read_yaml(PROFILE)
    raw['warehouse']['example_tasks'][0]['dropoff'] = 'inbound_1'
    for robot in raw['robots']:
        robot['nav2_params_path'] = str(PROFILE.parent/robot['nav2_params_path'])
    path.write_text(yaml.safe_dump(raw,allow_unicode=True))
    with pytest.raises(ValueError,match='invalid example task endpoints'):
        load_config(path)


def test_web_tasks_use_catalog_owner_session_and_idempotent_request(tmp_path):
    async def scenario(folder):
        config = load_config(PROFILE)
        core, _ = build_fleet_manager_from_config(PROFILE)
        snapshot = folder/'latest.json'
        socket = snapshot.with_suffix('.tasks.sock')
        with closing(SQLiteStore(tmp_path/'fleet.sqlite3')) as store:
            consumer = FleetEventLoop(store, core)
            await consumer.start()
            try:
                async with publish_fleet(consumer, snapshot, fleet_config=config):
                    app = create_app(snapshot, origins={ORIGIN}, fleet_config=config, task_socket=socket)
                    async with app.router.lifespan_context(app):
                        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as client:
                            for _ in range(100):
                                catalog = await client.get('/api/task-catalog')
                                if catalog.status_code == 200:
                                    break
                                await asyncio.sleep(.02)
                            body = catalog.json()
                            assert body['enabled'] and body['profile_digest'] == profile_digest(config)
                            request = dict(request_id=str(uuid4()), source_session_id=body['source_session_id'],
                                profile_digest=body['profile_digest'],pickup_id='inbound_1',dropoff_id='pick_B1',priority='LOW')
                            headers = {'Origin':ORIGIN}
                            denied = await client.post('/api/tasks',json=request)
                            assert denied.status_code == 403
                            accepted = await client.post('/api/tasks',json=request,headers=headers)
                            assert accepted.status_code == 201, accepted.text
                            duplicate = await client.post('/api/tasks',json=request,headers=headers)
                            assert duplicate.status_code == 200 and duplicate.json()['outcome'] == 'DUPLICATE'
                            conflict = await client.post('/api/tasks',json={**request,'dropoff_id':'pick_C2'},headers=headers)
                            assert conflict.status_code == 409
                            conflict = await client.post('/api/tasks',json={**request,'priority':'HIGH'},headers=headers)
                            assert conflict.status_code == 409
                            stale = await client.post('/api/tasks',json={**request,'source_session_id':'old'},headers=headers)
                            assert stale.status_code == 409
                            wrong_profile = await client.post('/api/tasks',json={**request,'profile_digest':'0'*64},headers=headers)
                            assert wrong_profile.status_code == 409
                            invalid = await client.post('/api/tasks',json={**request,'request_id':str(uuid4()),'dropoff_id':'inbound_2'},headers=headers)
                            assert invalid.status_code == 422
                            rows = store.connection.execute('SELECT snapshot FROM tasks').fetchall()
                            assert len(rows) == 1
                            saved = json.loads(rows[0][0])
                            destination = next(p for p in config.warehouse.transfer_points if p.id == 'pick_B1')
                            assert saved['dropoff_pose']['x'] == destination.pose.x
                            assert store.connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
                            assert not store.connection.execute('PRAGMA foreign_key_check').fetchall()
                            costmap = (await client.get('/api/warehouse-costmap')).json()
                            assert costmap['source'] == 'generated_occupancy'
                            assert sum(count for _,count in costmap['runs']) == costmap['width']*costmap['height']
            finally:
                await consumer.close()
            assert not socket.exists()
    with TemporaryDirectory(prefix='fleet-task-', dir='/tmp') as folder:
        asyncio.run(scenario(Path(folder)))


async def serve_host_queue(folder, port, origin):
    """Real API/consumer/SQLite acceptance endpoint without synthetic ROS robot status."""
    import uvicorn

    class HostServer(uvicorn.Server):
        @contextmanager
        def capture_signals(self):
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, setattr, self, 'should_exit', True)
            try:
                yield
            finally:
                for sig in (signal.SIGINT, signal.SIGTERM):
                    loop.remove_signal_handler(sig)

    folder.mkdir(parents=True, exist_ok=True)
    config = load_config(PROFILE)
    core, _ = build_fleet_manager_from_config(PROFILE)
    snapshot = folder/'latest.json'
    with closing(SQLiteStore(folder/'fleet.sqlite3')) as store:
        consumer = FleetEventLoop(store, core)
        await consumer.start()
        try:
            async with publish_fleet(consumer, snapshot, fleet_config=config):
                app = create_app(snapshot, origins={origin}, fleet_config=config,
                                 task_socket=snapshot.with_suffix('.tasks.sock'))
                await HostServer(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning')).serve()
        finally:
            await consumer.close()
            report = dict(tasks=[json.loads(row[0]) for row in store.connection.execute('SELECT snapshot FROM tasks')],
                          integrity=store.connection.execute('PRAGMA integrity_check').fetchone()[0],
                          foreign_keys=store.connection.execute('PRAGMA foreign_key_check').fetchall())
            (folder/'task-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Serve a real host-only task queue for Chrome acceptance')
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--origin', required=True)
    args = parser.parse_args()
    asyncio.run(serve_host_queue(args.state,args.port,args.origin))
