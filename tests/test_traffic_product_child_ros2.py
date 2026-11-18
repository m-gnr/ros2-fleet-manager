"""Generated IDL / existing service bridge, not a substitute for real BT evidence."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import threading
from types import SimpleNamespace as NS
from uuid import UUID, uuid4
import pytest

rclpy = pytest.importorskip('rclpy')
from fleet_interfaces.srv import RequestTrafficPermit
from unique_identifier_msgs.msg import UUID as ROSUUID
from nav2_msgs.action import NavigateToPose
from fleet_robot_executor.child_binding_ros import ROSChildBindingObserver
from fleet_robot_executor.node import RobotExecutorNode
from backend.fleet_manager.adapters.traffic_protocol import TrafficProtocolROSBridge, request_payload
from test_traffic_protocol import setup
from test_traffic_protocol_ros2 import FakeNode, path, wire


def identifier():return ROSUUID(uuid=list(uuid4().bytes))


def test_default_navigate_send_has_no_observation_uuid_or_bt_mutation():
    calls=[];sentinel=object()
    class Client:
        def send_goal_async(self,*args,**kwargs):
            calls.append((args,kwargs));return sentinel
    n=NS(_traffic_child_observer=None,_nav2_client=Client())
    goal=NavigateToPose.Goal();before=deepcopy(goal)
    assert RobotExecutorNode._send_nav2_observed(n,object(),goal,'PICKUP') is sentinel
    assert calls==[((goal,),{})] and goal==before


def actual_request(p):
    r=wire(p,path())
    r.context_id=identifier();r.nav_goal_uuid=identifier();r.observer_session_id=identifier()
    r.observation_seq=1;r.observation_kind=1
    return r


def test_actual_idl_bridge_commits_context_and_closes_without_ack(tmp_path):
    aio=asyncio.new_event_loop();thread=threading.Thread(target=aio.run_forever);thread.start()
    consumer=None
    try:
        consumer,p=asyncio.run_coroutine_threadsafe(setup(tmp_path),aio).result(3)
        bridge=TrafficProtocolROSBridge(FakeNode(),consumer,aio,{'r1':'/r1'})
        async def query(sql, params=()):
            return consumer.store.connection.execute(sql,params).fetchall()
        def rows(sql, params=()):
            return asyncio.run_coroutine_threadsafe(query(sql,params),aio).result(3)
        req=actual_request(p)
        response=bridge.request('r1',req,RequestTrafficPermit.Response()).decision
        assert response.committed and response.status=='RESERVED' and not response.movement_authorized
        parsed=request_payload(req,'r1')
        event_id='child:'+parsed['child_provenance']['context_id']+':1'
        row=rows('SELECT payload FROM traffic_decisions WHERE event_id=?',(event_id,))[0]
        assert json.loads(row[0])['payload']==json.loads(json.dumps(parsed))
        # Changing a source Path while keeping its digest never reaches consumer.
        changed=deepcopy(req);changed.path.poses[0].header.stamp.sec+=1
        assert not bridge.request('r1',changed,RequestTrafficPermit.Response()).decision.committed
        assert bridge.request('r1',req,RequestTrafficPermit.Response()).decision.reason=='CHILD_OBSERVATION_REPLAY'
        closed=deepcopy(req);closed.observation_seq=2;closed.observation_kind=2;closed.observation_reason='PARENT_CANCEL'
        assert bridge.request('r1',closed,RequestTrafficPermit.Response()).decision.status=='RECORDED'
        assert bridge.request('r1',req,RequestTrafficPermit.Response()).decision.status=='DENIED'
        ack_rows=rows("SELECT payload FROM traffic_decisions WHERE event_id LIKE 'traffic-ack:%'")
        assert ack_rows==[]
    finally:
        if consumer:
            asyncio.run_coroutine_threadsafe(consumer.close(),aio).result(3)
            aio.call_soon_threadsafe(consumer.store.close)
        aio.call_soon_threadsafe(aio.stop);thread.join(3);aio.close()


@pytest.mark.parametrize('field',['context_id','nav_goal_uuid','observer_session_id','observation_seq',
                                'child_terminal_status','observation_reason'])
def test_partial_evidence_cannot_fall_back_to_legacy_preparation(field):
    req=RequestTrafficPermit.Request()
    # A valid legacy envelope with a partially set provenance extension.
    req.robot_id='r1';req.movement_kind='PICKUP';req.path=path()
    from rclpy.serialization import serialize_message
    import hashlib
    req.path_digest=hashlib.sha256(serialize_message(req.path)).hexdigest()
    req.geometry=[0.,0.,1.,1.]
    value = 'PARTIAL' if field=='observation_reason' else (1 if field in ('observation_seq','child_terminal_status') else identifier())
    setattr(req,field,value)
    with pytest.raises(ValueError,match='Partial child provenance'):request_payload(req,'r1')


def test_tree_is_per_actual_parent_and_unqualified_nav_response_closes(tmp_path):
    n=FakeNode();n.state_machine.is_cancelling=False;n.nav2_action_name='/r1/navigate_to_pose'
    n.executor_config=NS(odometry_freshness_sec=1.)
    n._uuid_to_str=lambda value:str(UUID(bytes=bytes(value)))
    template=tmp_path/'template.xml'
    template.write_text('<root main_tree_to_execute="MainTree"><BehaviorTree ID="MainTree"><FollowPath path="{path}" controller_id="FollowPath"/></BehaviorTree></root>')
    profile=dict(template=str(template),output_dir=str(tmp_path/'trees'),frame='map',radius=.2,timeout=2.,
                 map_revision='m1',geometry_revision='g1')
    observer=ROSChildBindingObserver(n,profile)
    handle=NS(goal_id=ROSUUID(uuid=list(UUID(n.state_machine.active_goal_uuid).bytes)),
              request=NS(task_id='actual-parent',assignment_epoch=7))
    goal=NavigateToPose.Goal()
    nav,context=observer.begin(handle,goal,'PICKUP')
    old_bytes=Path(goal.behavior_tree).read_bytes()
    assert context.encode() in old_bytes and str(UUID(bytes=bytes(nav.uuid))).encode() in old_bytes
    assert bytes(nav.uuid)!=bytes(handle.goal_id.uuid)
    # No duck-typed handle can manufacture a real NavigateToPose acceptance.
    observer.confirm(context,NS(result=lambda:NS(accepted=True,goal_id=nav)))
    assert observer.binding.closed and not observer.events and not observer.decisions
    new_goal=NavigateToPose.Goal();observer.begin(handle,new_goal,'PICKUP')
    assert goal.behavior_tree!=new_goal.behavior_tree and Path(goal.behavior_tree).read_bytes()==old_bytes
    assert not observer.gate.send(lambda:pytest.fail('Motion opened'))
    with pytest.raises(ValueError):ROSChildBindingObserver(n,{**profile,'nonzero_enabled':True})
