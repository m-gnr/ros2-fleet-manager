"""Validated action progress; observations never replace RobotStatus authority."""
from dataclasses import dataclass
import math
from typing import Mapping


@dataclass(frozen=True)
class ActionFeedback:
    robot_id: str
    task_id: str
    assignment_epoch: int
    goal_uuid: str
    status_seq: int
    current_phase: int

    @classmethod
    def parse(cls, payload: Mapping):
        required = set(cls.__dataclass_fields__)
        observations = {'distance_to_goal', 'battery_soc'}
        missing, unknown = required - payload.keys(), payload.keys() - required - observations
        if missing or unknown:
            raise ValueError(f'Invalid ACTION_FEEDBACK fields: missing={sorted(missing)}, unknown={sorted(unknown)}')
        for key in ('robot_id', 'task_id', 'goal_uuid'):
            if not isinstance(payload[key], str) or not payload[key]:
                raise ValueError(f'ACTION_FEEDBACK {key} must be a nonempty string')
        for key in ('assignment_epoch', 'status_seq'):
            if type(payload[key]) is not int or not 1 <= payload[key] < 2**64:
                raise ValueError(f'ACTION_FEEDBACK {key} must be a positive uint64')
        if type(payload['current_phase']) is not int or payload['current_phase'] not in (1, 2, 3, 4):
            raise ValueError('ACTION_FEEDBACK current_phase must be a product transport phase')
        for key in observations & payload.keys():
            value = payload[key]
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f'ACTION_FEEDBACK {key} must be finite')
            if value < 0 or (key == 'battery_soc' and value > 100):
                raise ValueError(f'ACTION_FEEDBACK {key} is out of range')
        # Distance and feedback SoC are validated observations only. Physical pose,
        # energy and charging decisions continue to use authoritative RobotStatus.
        return cls(**{key: payload[key] for key in required})
