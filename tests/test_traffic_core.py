"""Targeted reservation-only domain and SQLite tests; no ROS/motion."""
import copy
from dataclasses import asdict, replace
import json
import tempfile
import threading
import unittest
from uuid import uuid4
from backend.fleet_manager.domain.traffic import *
from backend.fleet_manager.persistence.store import SQLiteStore, ScenarioResetRequired
from backend.fleet_manager.persistence.traffic import process_traffic
from backend.fleet_manager.event_loop import Event


def identity(robot='alpha'):
    return PermitIdentity(robot, 'task', 1, *(str(uuid4()) for _ in range(5)), 1, 'path', 'm1', 'map', 'g1')


def claim(i, name='a', points=((0, 0), (2, 0)), kind=ClaimKind.DYNAMIC_SWEEP):
    return TrafficAreaClaim(name, kind, i, sweep(points, .2), 1)


class Domain(unittest.TestCase):
    def setUp(self):
        self.core = TrafficCore('m1', 'map', 'g1', (Box(-10,-10,10,10),))
        self.a, self.b = identity(), identity('beta')
        self.core.bind(self.a); self.core.bind(self.b)

    def test_crossing_and_disjoint(self):
        self.assertEqual(self.core.acquire('a', [claim(self.a)])['status'], 'RESERVED')
        self.assertEqual(self.core.acquire('b', [claim(self.b, 'b', ((1,-2),(1,2)))])['reason'], 'GEOMETRIC_CONFLICT')
        self.assertEqual(self.core.acquire('c', [claim(self.b, 'c', ((0,3),(2,3)))])['status'], 'RESERVED')

    def test_static_dynamic_boundary(self):
        self.core.acquire('a', [claim(self.a, kind=ClaimKind.STATIC_ZONE)])
        self.assertEqual(self.core.acquire('b', [claim(self.b,'b',((0,.4),(2,.4)))])['reason'], 'GEOMETRIC_CONFLICT')

    def test_atomic_set(self):
        self.core.acquire('a', [claim(self.a)])
        result=self.core.acquire('b',[claim(self.b,'free',((0,3),(2,3))),claim(self.b,'hit')])
        self.assertEqual(result['status'],'DENIED');self.assertNotIn('free',self.core.state['claims'])

    def test_fencing_and_duplicate(self):
        c=claim(self.a); first=self.core.acquire('same',[c])
        self.assertEqual(first,self.core.acquire('same',[c]))
        for bad in (replace(self.a,epoch=2),replace(self.a,child_uuid=str(uuid4())),replace(self.a,generation=2),replace(self.a,executor_session=str(uuid4())),replace(self.a,map_revision='m2')):
            self.assertEqual(self.core.acquire(str(uuid4()),[claim(bad,'new')])['status'],'DENIED')
        self.assertEqual(self.core.acquire('same',[claim(self.a,'changed')])['reason'],'REQUEST_PAYLOAD_CHANGED')

    def test_stale_error_blocks_never_frees(self):
        self.core.acquire('a',[claim(self.a)])
        for reason in ('STALE','ERROR','TIMEOUT'):
            self.core.block('alpha',reason)
            self.assertEqual(self.core.state['claims']['a']['state'],'BLOCKED')
            self.assertEqual(self.core.state['claims']['a']['claim']['identity'],asdict(self.a))

    def test_release_unqualified(self):
        self.core.acquire('a',[claim(self.a)])
        self.assertEqual(self.core.release(ReleaseEvidence(self.a,('a',)))['reason'],'RELEASE_THRESHOLDS_UNVERIFIED')
        self.assertIn('a',self.core.state['claims'])

    def test_occupancy_violation_and_unmanaged(self):
        self.core.acquire('a',[claim(self.a)])
        observed=claim(self.b,'physical',kind=ClaimKind.PHYSICAL_OCCUPANCY)
        self.assertEqual(self.core.observe(observed)['status'],'ZONE_VIOLATION')
        self.assertEqual(self.core.state['claims']['a']['state'],'BLOCKED')
        self.assertIn('beta',self.core.state['claims']['a']['observed_occupants'])
        self.assertEqual(self.core.acquire('b',[claim(self.b,'b')])['status'],'DENIED')

    def test_unmanaged_segment_rotation_and_invalid(self):
        self.assertFalse(covered(Box(0,0,2,2),(Box(0,0,.9,2),Box(1.1,0,2,2))))
        self.assertEqual(self.core.acquire('far',[claim(self.a,points=((0,0),(20,0)))])['reason'],'UNMANAGED')
        self.assertEqual(len(sweep(((0,0),),.3)),1)
        with self.assertRaises(ValueError): sweep(((float('nan'),0),),.3)


class Persistence(unittest.TestCase):
    def setup_store(self, path):
        store=SQLiteStore(path)
        with store.transaction():
            process_traffic(store,Event('TRAFFIC_CONFIGURE',dict(revision='m1',frame='map',geometry_revision='g1',managed=[asdict(Box(-10,-10,10,10))])))
        return store

    def test_rollback_restart_and_outbox(self):
        with tempfile.TemporaryDirectory() as d:
            path=d+'/state.sqlite';s=self.setup_store(path); i=identity()
            with s.transaction(): process_traffic(s,Event('TRAFFIC_BIND',{'identity':asdict(i)}))
            event=Event('TRAFFIC_ACQUIRE',{'request_id':'r','claims':[asdict(claim(i))]})
            with self.assertRaises(RuntimeError):
                with s.transaction():
                    process_traffic(s,event)
                    raise RuntimeError('injected failure')
            self.assertIsNone(s.connection.execute('SELECT 1 FROM traffic_decisions WHERE event_id=?',(event.event_id,)).fetchone())
            with s.transaction(): result=process_traffic(s,event)
            with s.transaction(): self.assertEqual(result,process_traffic(s,event))
            self.assertEqual(s.connection.execute('SELECT count(*) FROM traffic_outbox WHERE event_id=?',(event.event_id,)).fetchone()[0],1)
            s.close();s=SQLiteStore(path)
            with self.assertRaises(ScenarioResetRequired):s.require_empty()
            self.assertIn('a',json.loads(s.connection.execute('SELECT snapshot FROM traffic_state').fetchone()[0])['state']['claims'])
            s.close()

    def test_concurrent_acquire(self):
        with tempfile.TemporaryDirectory() as d:
            path=d+'/state.sqlite';s=self.setup_store(path);a,b=identity(),identity('beta')
            for i in (a,b):
                with s.transaction():process_traffic(s,Event('TRAFFIC_BIND',{'identity':asdict(i)}))
            s.close();barrier=threading.Barrier(2);results=[];errors=[]
            def run(i):
                try:
                    store=SQLiteStore(path);barrier.wait(timeout=3)
                    with store.transaction():results.append(process_traffic(store,Event('TRAFFIC_ACQUIRE',{'request_id':i.robot_id,'claims':[asdict(claim(i,i.robot_id))]})))
                    store.close()
                except Exception as e: errors.append(e)
            threads=[threading.Thread(target=run,args=(i,)) for i in (a,b)]
            for t in threads:t.start()
            for t in threads:t.join(5)
            self.assertFalse(errors);self.assertEqual(sorted(r['status'] for r in results),['DENIED','RESERVED'])

class Consumer(unittest.TestCase):
    def test_consumer_stale_blocks_and_outbox_is_isolated(self):
        import asyncio
        from backend.fleet_manager.domain import FleetManagerCore, Pose2D
        from backend.fleet_manager.event_loop import FleetEventLoop
        class Routes:
            def get_path_distance(self, *args): return None
        async def run():
            s=SQLiteStore(':memory:')
            core=FleetManagerCore(Routes(),Pose2D());core.register_robot('alpha')
            loop=FleetEventLoop(s,core,clock=lambda:100.)
            await loop.start()
            try:
                await loop.submit(Event('TRAFFIC_CONFIGURE',dict(revision='m1',frame='map',geometry_revision='g1',managed=[asdict(Box(-10,-10,10,10))])))
                i=identity()
                await loop.submit(Event('TRAFFIC_BIND',{'identity':asdict(i)}))
                result=await loop.submit(Event('TRAFFIC_ACQUIRE',{'request_id':'a','claims':[asdict(claim(i))]}))
                self.assertFalse(result['movement_authorized'])
                await loop.submit(Event('TICK',{'current_time':100.}))
                state=json.loads(s.connection.execute('SELECT snapshot FROM traffic_state').fetchone()[0])['state']
                self.assertEqual(state['claims']['a']['state'],'BLOCKED')
                self.assertEqual(s.connection.execute('SELECT count(*) FROM outbox_events').fetchone()[0],0)
                self.assertGreater(s.connection.execute('SELECT count(*) FROM traffic_outbox').fetchone()[0],0)
            finally:
                await loop.close();s.close()
        asyncio.run(run())

class AdditionalGeometry(unittest.TestCase):
    setUp = Domain.setUp
    def test_static_static_and_claim_generation(self):
        self.core.acquire('a',[claim(self.a,kind=ClaimKind.STATIC_ZONE)])
        self.assertEqual(self.core.acquire('b',[claim(self.b,'b',kind=ClaimKind.STATIC_ZONE)])['reason'],'GEOMETRIC_CONFLICT')
        self.assertEqual(self.core.acquire('g',[replace(claim(self.a,'g'),claim_generation=2)])['reason'],'CLAIM_GENERATION_FENCE')

    def test_unmanaged_stop_hold_is_never_free(self):
        physical=claim(self.a,'stop',((20,20),),ClaimKind.STOP_HOLD)
        self.assertEqual(self.core.observe(physical)['status'],'ZONE_VIOLATION')
        self.assertTrue(self.core.state['global_block'])
        self.assertEqual(self.core.acquire('b',[claim(self.b)])['status'],'DENIED')
