"""Priority and FIFO task queue for Fleet Manager.

Implements approved requirements:
- Priority order: HIGH (1) -> MEDIUM (2) -> LOW (3)
- Work-conserving FIFO within each priority tier (sorted by created_at)
- No starvation aging for pending tasks in MVP (C3-DEC-04)
- Preserving original created_at on preemption requeue (DOC-ARCH Sec 6.2, Karar 08 T09)
"""

from typing import Dict, Iterator, List, Optional

from .constants import TaskPriority, TaskStatus
from .models import Task


class TaskQueue:
    """Multi-priority work-conserving task queue.
    
    Tasks are organized into three distinct priority classes:
    - HIGH (TaskPriority.PRIORITY_HIGH = 1)
    - MEDIUM (TaskPriority.PRIORITY_MEDIUM = 2)
    - LOW (TaskPriority.PRIORITY_LOW = 3)
    
    Within each class, tasks are strictly ordered by `created_at` ascending (FIFO).
    """

    def __init__(self) -> None:
        self._queues: Dict[int, List[Task]] = {
            TaskPriority.PRIORITY_HIGH: [],
            TaskPriority.PRIORITY_MEDIUM: [],
            TaskPriority.PRIORITY_LOW: [],
        }
        self._tasks_by_id: Dict[str, Task] = {}

    def enqueue(self, task: Task) -> None:
        """Add a new task to the queue based on its priority and created_at.
        
        Raises ValueError if task_id already exists.
        """
        if task.task_id in self._tasks_by_id:
            raise ValueError(f"Task with id {task.task_id} already exists in queue")

        if task.priority not in self._queues:
            raise ValueError(f"Unsupported task priority: {task.priority}")

        task.status = TaskStatus.QUEUED
        self._insert_sorted(self._queues[task.priority], task)
        self._tasks_by_id[task.task_id] = task

    def requeue_preempted(self, task: Task) -> None:
        """Requeue a preempted task with its original created_at timestamp.
        
        This guarantees that the preempted task keeps its FIFO rank relative
        to all newer tasks in the same priority class (Karar 08 Politika P05 / T09).
        """
        task.status = TaskStatus.QUEUED
        # Clear assignment fields
        task.assigned_robot_id = None
        task.assignment_epoch = None
        task.goal_uuid = None

        if task.priority not in self._queues:
            raise ValueError(f"Unsupported task priority: {task.priority}")

        # If it was already in lookup dict, re-insert sorted
        self._insert_sorted(self._queues[task.priority], task)
        self._tasks_by_id[task.task_id] = task

    def remove(self, task_id: str) -> Optional[Task]:
        """Remove and return task by id from queue if present."""
        task = self._tasks_by_id.pop(task_id, None)
        if task is not None:
            q = self._queues.get(task.priority, [])
            for i, t in enumerate(q):
                if t.task_id == task_id:
                    q.pop(i)
                    break
        return task

    def get(self, task_id: str) -> Optional[Task]:
        """Lookup task by id without removing it."""
        return self._tasks_by_id.get(task_id)

    def iter_assignable_tasks(self) -> Iterator[Task]:
        """Iterate over all queued tasks in strict dispatch order:
        
        1. HIGH priority tasks (FIFO by created_at)
        2. MEDIUM priority tasks (FIFO by created_at)
        3. LOW priority tasks (FIFO by created_at)
        
        Note: Does not apply aging in MVP (C3-DEC-04).
        If a task cannot be assigned in this round, caller skips it and continues
        evaluating the next candidate without modifying the queue.
        """
        for priority in (
            TaskPriority.PRIORITY_HIGH,
            TaskPriority.PRIORITY_MEDIUM,
            TaskPriority.PRIORITY_LOW,
        ):
            # Iterate over shallow copy to allow removal during iteration if desired
            for task in list(self._queues[priority]):
                if task.status == TaskStatus.QUEUED:
                    yield task

    def peek_highest_priority(self) -> Optional[Task]:
        """Return the next task at the head of the dispatch order without removing it."""
        for task in self.iter_assignable_tasks():
            return task
        return None

    def __len__(self) -> int:
        """Return total count of queued tasks."""
        return sum(len(q) for q in self._queues.values())

    def count_by_priority(self, priority: int) -> int:
        """Return count of queued tasks for a given priority."""
        return len(self._queues.get(priority, []))

    def _insert_sorted(self, queue_list: List[Task], task: Task) -> None:
        """Insert task into queue_list maintaining created_at ascending order."""
        # Binary insertion or simple linear insertion (queues in MVP are small)
        insert_idx = len(queue_list)
        for i, existing in enumerate(queue_list):
            if task.created_at < existing.created_at:
                insert_idx = i
                break
        queue_list.insert(insert_idx, task)
