"""Isolated adapter-to-consumer contract probe; never connects to ROS or the live database."""
import asyncio
from contextlib import closing
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

from backend.fleet_manager.adapters.action_client import ExecuteTaskActionClientBridge
from backend.fleet_manager.domain import FleetManagerCore, Pose2D
from backend.fleet_manager.event_loop import Event, FleetEventLoop
from backend.fleet_manager.persistence import SQLiteStore


class Routes:
    def get_path_distance(self, *_):
        return 1.0


async def probe():
    report=dict(scope='ISOLATED_CONTRACT_PROBE_NOT_PHYSICAL_EVIDENCE',errors=[],events=[])
    with tempfile.TemporaryDirectory() as folder, closing(SQLiteStore(Path(folder)/'probe.sqlite3')) as store:
        core=FleetManagerCore(Routes(),Pose2D())
        core.register_robot('probe_robot')
        consumer=FleetEventLoop(store,core,clock=lambda:10.)
        await consumer.start()
        try:
            await consumer.submit(Event('ROBOT_STATUS',dict(robot_id='probe_robot',status_seq=1,current_epoch=0,
                current_task_id=None,state=1,current_phase=0,is_loaded=False,pose=Pose2D(),battery_soc_percent=100.,
                battery_energy_wh=100.,timestamp_sec=10.,publisher_session_id=None)))
            await consumer.submit(Event('SUBMIT_TASK',dict(task_id='probe_task',pickup_pose=Pose2D(1,0),
                dropoff_pose=Pose2D(2,0),priority=3,created_at=1.)))
            await consumer.submit(Event('TICK',dict(current_time=10.)))
            task=consumer.core._active_tasks['probe_task']
            report['before']=task.status
            class Observe:
                async def submit(self,event):
                    report['events'].append(dict(kind=event.kind,payload=event.payload))
                    try:
                        return await consumer.submit(event)
                    except Exception as error:
                        report['errors'].append(dict(type=type(error).__name__,message=str(error)))
                        raise
            bridge=ExecuteTaskActionClientBridge('probe_robot',Observe(),asyncio.get_running_loop())
            bridge._handle_feedback(task.task_id,task.goal_uuid,task.assignment_epoch,
                SimpleNamespace(feedback=SimpleNamespace(current_phase=1,distance_to_goal=1.,battery_soc=100.)))
            for _ in range(50):
                if report['errors'] or consumer.core._active_tasks['probe_task'].status=='EXECUTING':
                    break
                await asyncio.sleep(.01)
            report['after']=consumer.core._active_tasks['probe_task'].status
            report['committed_feedback_events']=store.connection.execute(
                "SELECT count(*) FROM processed_events WHERE stream LIKE 'feedback:%'").fetchone()[0]
            report['result']='geçti' if report['after']=='EXECUTING' and not report['errors'] else 'başarısız'
        finally:
            await consumer.close()
    print(json.dumps(report,indent=2))
    return 0 if report['result']=='geçti' else 1


if __name__=='__main__':
    raise SystemExit(asyncio.run(probe()))
