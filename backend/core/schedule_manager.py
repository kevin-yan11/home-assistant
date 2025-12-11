"""
Schedule Manager - Manages scheduled tasks and reminders.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid


class TaskType(Enum):
    DEVICE_CONTROL = "device_control"
    REMINDER = "reminder"


class RepeatType(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    id: str
    task_type: TaskType
    trigger_time: datetime
    repeat: RepeatType
    description: str
    action: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)


class ScheduleManager:
    """In-memory schedule storage for demo purposes."""

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}

    def create_task(
        self,
        task_type: str,
        trigger_time: datetime,
        description: str,
        repeat: str = "once",
        action: Dict[str, Any] = None,
        message: str = ""
    ) -> ScheduledTask:
        """Create a new scheduled task."""
        task_id = str(uuid.uuid4())[:8]
        task = ScheduledTask(
            id=task_id,
            task_type=TaskType(task_type),
            trigger_time=trigger_time,
            repeat=RepeatType(repeat),
            description=description,
            action=action or {},
            message=message,
            status=TaskStatus.PENDING,
        )
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.CANCELLED
            return True
        return False

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed."""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if task.repeat == RepeatType.ONCE:
                task.status = TaskStatus.COMPLETED
            else:
                # Reschedule recurring tasks
                if task.repeat == RepeatType.DAILY:
                    task.trigger_time += timedelta(days=1)
                elif task.repeat == RepeatType.WEEKLY:
                    task.trigger_time += timedelta(weeks=1)
            return True
        return False

    def get_pending_tasks(self) -> List[ScheduledTask]:
        """Get all pending tasks."""
        return [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]

    def get_due_tasks(self) -> List[ScheduledTask]:
        """Get tasks that are due for execution."""
        now = datetime.now()
        return [
            t for t in self._tasks.values()
            if t.status == TaskStatus.PENDING and t.trigger_time <= now
        ]

    def get_all_tasks(self) -> List[ScheduledTask]:
        """Get all tasks."""
        return list(self._tasks.values())

    def get_context(self) -> str:
        """Generate context string for agent prompt injection."""
        pending = self.get_pending_tasks()
        if not pending:
            return "[Scheduled Tasks]\nNo scheduled tasks."

        lines = ["[Scheduled Tasks]"]
        for task in sorted(pending, key=lambda t: t.trigger_time):
            time_str = task.trigger_time.strftime("%Y-%m-%d %H:%M")
            repeat_str = f" ({task.repeat.value})" if task.repeat != RepeatType.ONCE else ""
            if task.task_type == TaskType.REMINDER:
                lines.append(f"- [{task.id}] {time_str}{repeat_str}: Reminder - {task.message}")
            else:
                lines.append(f"- [{task.id}] {time_str}{repeat_str}: {task.description}")
        return "\n".join(lines)

    def delete_task(self, task_id: str) -> bool:
        """Permanently delete a task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False


schedule_manager = ScheduleManager()
