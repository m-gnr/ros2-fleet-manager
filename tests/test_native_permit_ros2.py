"""Generated ROS String transport with fake endpoints; no native hardware claim."""
import asyncio
from copy import deepcopy
import json
import threading
import time
from types import SimpleNamespace as NS
import pytest

rclpy=pytest.importorskip('rclpy')
from std_msgs.msg import String
from fleet_config.native_zero import compact,sign
from fleet_robot_executor.native_zero import NativeZeroLink
from fleet_robot_executor.traffic import MovementGate
from backend.fleet_manager.adapters.native_zero import NativeZeroROSBridge
from test_traffic_protocol_ros2 import FakeNode
from test_native_permit_context import start,exchange,KEY


def test_keyless_executor_forwards_exact_matching_zero_and_revoke_only(tmp_path):
    async def run():
        c,p,b,d,s=await start(tmp_path)
        try:
            transfer=(await c.submit(exchange(p,s)))['transfer']
            gate=MovementGate();gate.prepare(p,2.)
            assert gate.receive({**d,'committed':True})
            assert gate.observe_child_accepted(p['child_uuid'],bytes.fromhex(p['path_bytes']))
            n=FakeNode();observer=NS(gate=gate,close=lambda reason:gate.revoke(reason))
            link=NativeZeroLink(n,observer)
            signed=json.loads(exchange(p,s).payload['native_status'])
            link.state(String(data=compact(dict(native_status=signed))))
            wire=sign(transfer['body'],KEY);link.envelope(String(data=wire))
            assert n.sent[-1].data==wire and not hasattr(link,'key')
            assert gate.applied is None and not gate.send(lambda:pytest.fail('Movement opened'))
            changed=json.loads(transfer['body']);changed['velocity'][0]=.2
            before=len(link.forwarded);link.envelope(String(data=sign(compact(changed),KEY)))
            assert len(link.forwarded)==before
            gate.revoke('REPLAN');link.envelope(String(data=wire));assert len(link.forwarded)==before
            revoke=json.loads(transfer['body']);revoke['command_sequence']+=1
            revoke['command_context']['operation']='REVOKE_ZERO'
            link.envelope(String(data=sign(compact(revoke),KEY)))
            assert link.forwarded[-1]['operation']=='REVOKE_ZERO'
            assert gate.applied is None
        finally:await c.close();c.store.close()
    asyncio.run(run())


@pytest.mark.parametrize('fault',['rollback','publish_loss'])
def test_transport_never_publishes_before_commit_and_retry_has_identical_body(tmp_path,fault):
    loop=asyncio.new_event_loop();thread=threading.Thread(target=loop.run_forever);thread.start()
    c=None
    try:
        c,p,b,d,s=asyncio.run_coroutine_threadsafe(start(tmp_path),loop).result(3)
        n=FakeNode();bridge=NativeZeroROSBridge(n,c,loop,{'r1':'/r1'})
        async def query(sql,params=()):return c.store.connection.execute(sql,params).fetchall()
        def read(sql,params=()):return asyncio.run_coroutine_threadsafe(query(sql,params),loop).result(3)
        if fault=='rollback':
            read("CREATE TRIGGER fail_native BEFORE INSERT ON traffic_outbox WHEN NEW.event_id LIKE 'native-transfer:%' BEGIN SELECT RAISE(ABORT,'native rollback'); END")
        else:
            def lost(_):raise RuntimeError('Injected publish loss after COMMIT')
            bridge.publishers['r1']=NS(publish=lost)
        payload=exchange(p,s).payload
        message=String(data=compact(dict(request_id=p['request_id'],native_status=payload['native_status'])))
        bridge.exchange('r1',message)
        end=time.monotonic()+3
        while bridge.pending and time.monotonic()<end:time.sleep(.01)
        assert not n.sent
        prepared=read("SELECT decision FROM traffic_decisions WHERE event_id LIKE 'native-transfer:%'")
        assert len(prepared)==(0 if fault=='rollback' else 1)
        assert not read("SELECT 1 FROM traffic_decisions WHERE event_id LIKE 'native-ack:%'")
        if fault=='publish_loss':
            bridge.publishers['r1']=NS(publish=lambda value:n.sent.append(deepcopy(value)))
            s['report_sequence']+=1;payload=exchange(p,s).payload
            bridge.exchange('r1',String(data=compact(dict(request_id=p['request_id'],native_status=payload['native_status']))))
            end=time.monotonic()+3
            while bridge.pending and time.monotonic()<end:time.sleep(.01)
            assert json.loads(n.sent[0].data)['body']==json.loads(prepared[0][0])['body']
            assert not read("SELECT 1 FROM traffic_decisions WHERE event_id LIKE 'native-ack:%'")
    finally:
        if c:
            asyncio.run_coroutine_threadsafe(c.close(),loop).result(3);loop.call_soon_threadsafe(c.store.close)
        loop.call_soon_threadsafe(loop.stop);thread.join(3);loop.close()
