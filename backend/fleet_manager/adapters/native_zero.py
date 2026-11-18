"""Optional B6B.7 transport: sign only the body returned after consumer COMMIT."""
import asyncio
from fleet_config.native_zero import compact, strict, sign
from ..event_loop import Event
from ..domain.constants import RobotState


def traffic_start_ready(core, now):
    """Fixture admission only; never unblocks a stale/session-fenced robot."""
    robots = core.tracker.list_robots()
    return bool(robots) and all(
        r.initial_status_verified and not r.session_blocked and not r.is_stale(now)
        and r.state != RobotState.STATE_ERROR for r in robots)


class NativeZeroROSBridge:
    def __init__(self, node, consumer, loop, namespaces):
        from std_msgs.msg import String
        if consumer._native_zero_profile is None:
            raise ValueError('Explicit native zero test seam required')
        self.consumer,self.loop = consumer,loop
        self.publishers,self.subscriptions = {},[]
        self.pending = set()
        for robot,namespace in namespaces.items():
            self.publishers[robot] = node.create_publisher(String,namespace+'/native_permit_envelope',16)
            self.subscriptions.append(node.create_subscription(String,namespace+'/native_permit_exchange',
                lambda message,robot=robot:self.exchange(robot,message),16))

    def exchange(self,robot,message):
        from std_msgs.msg import String
        # At most one outstanding consumer exchange per robot. No SQLite/network wait in ROS.
        if robot in self.pending:return
        try:
            p = strict(message.data)
            if set(p) != {'request_id','native_status'}:return
            p['robot_id'] = robot
        except (ValueError,TypeError,RecursionError):return
        self.pending.add(robot)
        future=asyncio.run_coroutine_threadsafe(self.consumer.submit(Event('TRAFFIC_PROTOCOL_NATIVE_EXCHANGE',p)),self.loop)
        def completed(done):
            try:
                result=done.result()
                if result.get('transfer'):
                    # The durable body is immutable across a retry. Never manufacture an ACK.
                    body=result['transfer']['body']
                    wire=sign(body,self.consumer._native_zero_profile['keys'][robot])
                    self.publishers[robot].publish(String(data=wire))
            except Exception:
                pass  # No fresh zero reaches native: its existing lease expires.
            finally:self.pending.discard(robot)
        future.add_done_callback(completed)
