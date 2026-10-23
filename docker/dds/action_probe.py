"""Temporary action transport evidence; not ExecuteTask or robot policy."""

import json
import math
import os
import sys
import time
import uuid

import rclpy
from action_msgs.msg import GoalStatus
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy.utilities import get_rmw_implementation_identifier
from dds_probe_interfaces.action import TransportProbe


def event(name, **data):
    print(json.dumps(dict(event=name, **data)), flush=True)


def main():
    role = os.environ['DDS_ROLE']
    name = os.environ['DDS_ACTION_NAME']
    token = os.environ['DDS_TEST_PAYLOAD']
    timeout = float(os.environ['DDS_TEST_TIMEOUT_SECONDS'])
    period = float(os.environ['DDS_PUBLISH_PERIOD_SECONDS'])
    if role not in ('server', 'client'):
        raise ValueError('DDS_ROLE must be server or client')
    if not name.startswith('/') or not token:
        raise ValueError('Absolute DDS_ACTION_NAME and nonempty DDS_TEST_PAYLOAD required')
    if not all(math.isfinite(v) and v > 0 for v in (timeout, period)):
        raise ValueError('Timeout and period must be positive finite seconds')
    if not 0 <= int(os.environ['ROS_DOMAIN_ID']) <= 232:
        raise ValueError('ROS_DOMAIN_ID must be in 0..232')
    if os.environ['ROS_LOCALHOST_ONLY'] != '0':
        raise ValueError('ROS_LOCALHOST_ONLY must be 0 for this container test')
    rclpy.init()
    node = rclpy.create_node('action_probe_' + role)
    event('START', role=role, action=name, rmw=get_rmw_implementation_identifier())
    endpoint = None
    executor = None
    try:
        if role == 'server':
            def execute(goal):
                proof = goal.request.token + ':' + uuid.uuid4().hex
                deadline = time.monotonic() + timeout
                count = 0
                while rclpy.ok() and time.monotonic() < deadline:
                    if goal.is_cancel_requested:
                        goal.canceled()
                        result = TransportProbe.Result(proof=proof + ':canceled')
                        event('SERVER_CANCELED', proof=result.proof)
                        return result
                    goal.publish_feedback(TransportProbe.Feedback(proof=proof))
                    count += 1
                    if not goal.request.cancel_probe and count >= 3:
                        goal.succeed()
                        result = TransportProbe.Result(proof=proof + ':succeeded')
                        event('SERVER_SUCCEEDED', proof=result.proof)
                        return result
                    time.sleep(period)
                # This guard bounds the test fixture; it is not fleet timeout policy.
                goal.abort()
                return TransportProbe.Result(proof='fixture guard expired')

            def accept(request):
                event('SERVER_GOAL', token=request.token, cancel_probe=request.cancel_probe)
                return GoalResponse.ACCEPT

            def cancel(goal):
                event('SERVER_CANCEL', token=goal.request.token)
                return CancelResponse.ACCEPT

            endpoint = ActionServer(node, TransportProbe, name, execute,
                                    goal_callback=accept, cancel_callback=cancel,
                                    callback_group=ReentrantCallbackGroup())
            executor = MultiThreadedExecutor(num_threads=2)
            executor.add_node(node)
            executor.spin()
            return 0

        endpoint = ActionClient(node, TransportProbe, name)
        if not endpoint.wait_for_server(timeout_sec=timeout):
            raise RuntimeError('Test guard: server discovery expired')

        def wait_until(predicate):
            deadline = time.monotonic() + timeout
            while rclpy.ok() and not predicate():
                if time.monotonic() >= deadline:
                    raise RuntimeError('Test guard: expected transport event missing')
                rclpy.spin_once(node, timeout_sec=0.1)
            if not predicate():
                raise RuntimeError('Interrupted before transport evidence')

        def resolve(future):
            wait_until(future.done)
            return future.result()

        for cancel_probe in (False, True):
            case = 'cancel' if cancel_probe else 'complete'
            case_token = token + ':' + case
            feedback = []

            def receive(message):
                feedback.append((bytes(message.goal_id.uuid), message.feedback.proof))
                event('FEEDBACK_RECEIVED', case=case, proof=message.feedback.proof)

            handle = resolve(endpoint.send_goal_async(
                TransportProbe.Goal(token=case_token, cancel_probe=cancel_probe),
                feedback_callback=receive))
            if not handle.accepted:
                raise RuntimeError('Probe goal was not accepted')
            event('GOAL_ACCEPTED', case=case, uuid=bytes(handle.goal_id.uuid).hex())
            result_future = handle.get_result_async()
            wait_until(lambda: bool(feedback))
            if cancel_probe:
                response = resolve(handle.cancel_goal_async())
                if response.return_code != 0 or not any(
                    bytes(g.goal_id.uuid) == bytes(handle.goal_id.uuid)
                    for g in response.goals_canceling
                ):
                    raise RuntimeError('Cancel response did not confirm this goal')
                event('CANCEL_ACCEPTED', case=case, return_code=response.return_code)
            result = resolve(result_future)
            expected_status = (GoalStatus.STATUS_CANCELED if cancel_probe
                               else GoalStatus.STATUS_SUCCEEDED)
            suffix = ':canceled' if cancel_probe else ':succeeded'
            proof = feedback[0][1]
            if not proof.startswith(case_token + ':') or len(proof) != len(case_token) + 33:
                raise RuntimeError('Feedback does not contain run token and server nonce')
            if any(gid != bytes(handle.goal_id.uuid) or value != proof
                   for gid, value in feedback):
                raise RuntimeError('Feedback goal UUID or content mismatch')
            if result.status != expected_status or result.result.proof != proof + suffix:
                raise RuntimeError('Terminal result status or server content mismatch')
            event('RESULT_RECEIVED', case=case, status=result.status, proof=result.result.proof)
            event('CASE_PASS', case=case)
        event('PASS')
        return 0
    except (KeyboardInterrupt, ExternalShutdownException):
        return 0 if role == 'server' else 1
    except Exception as exc:
        event('FAIL', reason=str(exc))
        return 1
    finally:
        if executor is not None:
            executor.shutdown()
        if endpoint is not None:
            endpoint.destroy()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    sys.exit(main())
