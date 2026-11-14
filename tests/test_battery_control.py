"""Battery controls scale with the authoritative inventory, never with a fixed pair."""
import asyncio
from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient
from fastapi import HTTPException
import pytest

from backend.dashboard.api import create_app
from backend.dashboard.battery_control import BatteryCommand, BatteryControls
from fleet_config import load_config
from fleet_config.models import BatteryModel, Robot
from fleet_battery_simulator.consumption import BatteryConsumption

TOKEN = 'test-only-battery-control-token-123456789'
ORIGIN = 'http://127.0.0.1:32101'


def config_three():
    config = load_config('config/fleet.yaml')
    third = config.robots[0].model_copy(update=dict(id='synthetic_third', name='third', namespace='/test/third',
        nav2_action_name='/test/third/navigate_to_pose', initial_pose=config.robots[0].initial_pose.model_copy(update={'x': 12.0})))
    return type(config).model_validate({**config.model_dump(), 'robots': [*(r.model_dump() for r in config.robots), third.model_dump()]})


class Gateway:
    def __init__(self, config):
        self.batteries = {r.id: BatteryConsumption(config.fleet.battery_models[r.battery_model]) for r in config.robots}
        self.sessions = {r.id: 'session-' + r.id for r in config.robots}
        self.failed = set()
        self.lost_ack = set()
        self.calls = []

    async def read(self, robot):
        if robot.id in self.failed:
            raise ValueError('Service disconnected')
        return dict(robot_id=robot.id, session_id=self.sessions[robot.id], **self.batteries[robot.id].control_state())

    async def apply(self, robot, command, session):
        self.calls.append((robot.id, robot.namespace))
        self.batteries[robot.id].control(soc=command.soc_percent, mode=command.mode,
            discharge_minutes=command.discharge_minutes, charge_minutes=command.charge_minutes)
        if robot.id in self.lost_ack:
            raise TimeoutError('Acknowledgement lost')
        return await self.read(robot)


def command(gateway, **kwargs):
    return BatteryCommand(request_id='test-command', all_robots=True, confirm_bulk_soc=True,
        safe_test_environment=True, sessions=gateway.sessions.copy(), soc_percent=25., mode='FAST', **kwargs)


@pytest.mark.parametrize('capacity', [40., 100., 350.])
def test_capacity_based_fast_targets_and_normal_restore(capacity):
    model = BatteryModel(usable_capacity_wh=capacity, consumption_wh_per_meter=.4, idle_power_w=2., charge_power_w=20.)
    battery = BatteryConsumption(model)
    battery.control(mode='FAST')
    battery.update_clock(0)
    battery.update_clock(600_000_000_000)
    assert battery.soc_percent == pytest.approx(25)
    battery.update_clock(1_200_000_000_000, charging=True)
    assert battery.soc_percent == pytest.approx(80)
    battery.control(mode='NORMAL')
    assert battery.control_state()['idle_power_w'] == 2
    assert battery.control_state()['charge_power_w'] == 20
    assert battery.control_state()['consumption_wh_per_meter'] == .4


@pytest.mark.parametrize('changes', [dict(soc=-1), dict(soc=101), dict(soc=float('nan')),
    dict(soc=20, mode='invalid'), dict(soc=20, mode='FAST', discharge_minutes=0),
    dict(soc=20, mode='FAST', charge_minutes=float('inf')), dict(mode='FAST', charge_minutes=1441)])
def test_invalid_control_is_atomic(changes):
    config = config_three()
    battery = BatteryConsumption(next(iter(config.fleet.battery_models.values())))
    before = battery.control_state()
    with pytest.raises(ValueError):
        battery.control(**changes)
    assert battery.control_state() == before


def test_dynamic_three_partial_failure_and_readback():
    async def run():
        config = config_three()
        gateway = Gateway(config)
        gateway.failed.add(config.robots[1].id)
        controls = BatteryControls(config, gateway)
        inventory = await controls.inventory()
        assert len(inventory['robots']) == 3
        assert inventory['robots'][2]['namespace'] == '/test/third'
        result = await controls.apply(command(gateway))
        assert result['atomic'] is False and not result['all_verified']
        assert [r['outcome'] for r in result['results']] == ['VERIFIED', 'REJECTED', 'VERIFIED']
        assert result['results'][2]['readback']['soc_percent'] == 25
        assert ('synthetic_third', '/test/third') in gateway.calls
        assert gateway.batteries[config.robots[1].id].soc_percent == 100
    asyncio.run(run())


def test_lost_ack_and_session_change_never_report_success():
    async def run():
        config = config_three()
        gateway = Gateway(config)
        controls = BatteryControls(config, gateway)
        cmd = command(gateway)
        gateway.sessions[config.robots[0].id] = 'restarted'
        gateway.lost_ack.add(config.robots[1].id)
        result = await controls.apply(cmd)
        assert [r['outcome'] for r in result['results']] == ['REJECTED', 'UNVERIFIED', 'VERIFIED']
        assert len(gateway.calls) == 2
    asyncio.run(run())


def test_http_auth_bulk_confirm_and_unknown_robot(tmp_path):
    config = config_three()
    gateway = Gateway(config)
    app = create_app(tmp_path / 'absent.json', origins={ORIGIN}, fleet_config=config,
                     battery_gateway=gateway, battery_token=TOKEN)
    headers = {'authorization': 'Bearer ' + TOKEN, 'origin': ORIGIN}
    with TestClient(app, base_url='http://127.0.0.1') as client:
        assert client.get('/api/sim/batteries').status_code == 401
        assert len(client.get('/api/sim/batteries', headers=headers).json()['robots']) == 3
        payload = command(gateway).model_dump()
        assert client.post('/api/sim/batteries', json=payload).status_code == 401
        assert client.post('/api/sim/batteries', json=payload, headers={**headers, 'origin': 'http://foreign.test'}).status_code == 403
        for field in ('safe_test_environment', 'confirm_bulk_soc'):
            invalid = {**payload, field: False}
            assert client.post('/api/sim/batteries', json=invalid, headers=headers).status_code == 409
        assert not gateway.calls
        assert client.post('/api/sim/batteries', json={**payload, 'soc_percent': 101}, headers=headers).status_code == 422
        assert client.post('/api/sim/batteries', json={**payload, 'robot_id': 'unknown', 'all_robots': False}, headers=headers).status_code == 404
        response = client.post('/api/sim/batteries', json=payload, headers=headers)
        assert response.status_code == 200 and response.json()['all_verified']


def test_single_target_isolation_and_capacity_mismatch():
    async def run():
        config = config_three()
        gateway = Gateway(config)
        controls = BatteryControls(config, gateway)
        target = config.robots[2].id
        cmd = BatteryCommand(request_id='one-only', robot_id=target, safe_test_environment=True,
                             sessions={target: gateway.sessions[target]}, soc_percent=0.)
        response = await controls.apply(cmd)
        assert response['all_verified']
        assert gateway.batteries[target].soc_percent == 0
        assert all(gateway.batteries[r.id].soc_percent == 100 for r in config.robots[:2])
        gateway.batteries[target].capacity_wh *= 2
        assert not (await controls.inspect(target))['available']
        assert (await controls.inspect(config.robots[0].id))['available']
    asyncio.run(run())


def test_requested_profile_must_match_actual_simulator_readback():
    async def run():
        config = config_three()
        gateway = Gateway(config)
        async def ignore_profile(robot, cmd, session):
            return await gateway.read(robot)
        gateway.apply = ignore_profile
        result = await BatteryControls(config, gateway).apply(command(gateway))
        assert not result['all_verified']
        assert all(r['outcome'] == 'UNVERIFIED' for r in result['results'])
    asyncio.run(run())
