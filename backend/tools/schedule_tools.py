"""
Schedule tools for creating, managing, and querying scheduled tasks.
"""
from datetime import datetime, timedelta
from agentscope.tool import ToolResponse
from core.schedule_manager import schedule_manager


def parse_time_expression(time_expr: str) -> datetime:
    """
    Parse various time expressions into datetime.
    Supports: "10 minutes", "1 hour", "2023-12-25 14:00", "tomorrow 9:00", etc.
    """
    time_expr = time_expr.lower().strip()
    now = datetime.now()

    # Relative time: "in X minutes/hours"
    if "minute" in time_expr:
        minutes = int(''.join(filter(str.isdigit, time_expr)) or 10)
        return now + timedelta(minutes=minutes)
    elif "hour" in time_expr:
        hours = int(''.join(filter(str.isdigit, time_expr)) or 1)
        return now + timedelta(hours=hours)

    # Tomorrow
    if "tomorrow" in time_expr:
        # Extract time if present
        import re
        time_match = re.search(r'(\d{1,2}):?(\d{2})?', time_expr)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
        else:
            hour, minute = 9, 0  # Default to 9:00
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Today with time
    if "today" in time_expr:
        import re
        time_match = re.search(r'(\d{1,2}):?(\d{2})?', time_expr)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or 0)
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Absolute datetime: "2023-12-25 14:00" or "14:00"
    try:
        # Try full datetime
        return datetime.strptime(time_expr, "%Y-%m-%d %H:%M")
    except ValueError:
        pass

    try:
        # Try time only (today)
        time_obj = datetime.strptime(time_expr, "%H:%M")
        return now.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
    except ValueError:
        pass

    # Default: 10 minutes from now
    return now + timedelta(minutes=10)


def create_reminder(
    message: str,
    time: str,
    repeat: str = "once"
) -> ToolResponse:
    """
    Create a reminder for the user.

    Args:
        message: What to remind the user about
        time: When to trigger (e.g., "10 minutes", "tomorrow 9:00", "14:30")
        repeat: Frequency - "once", "daily", or "weekly"
    """
    trigger_time = parse_time_expression(time)
    task = schedule_manager.create_task(
        task_type="reminder",
        trigger_time=trigger_time,
        description=f"Reminder: {message}",
        repeat=repeat,
        message=message,
    )
    time_str = trigger_time.strftime("%Y-%m-%d %H:%M")
    repeat_info = f" (repeats {repeat})" if repeat != "once" else ""
    return ToolResponse(
        content=f"Reminder set for {time_str}{repeat_info}: {message} [ID: {task.id}]"
    )


def create_device_schedule(
    description: str,
    time: str,
    device_type: str,
    room: str,
    action: str,
    repeat: str = "once",
    parameters: str = None
) -> ToolResponse:
    """
    Schedule a device control action.

    Args:
        description: What this schedule does (e.g., "turn on bedroom light")
        time: When to trigger (e.g., "07:00", "tomorrow 18:00")
        device_type: Type of device - light, ac, or speaker
        room: Room name
        action: Action to perform (turn_on, turn_off, dim, set_temp, play, etc.)
        repeat: Frequency - "once", "daily", or "weekly"
        parameters: JSON string of additional parameters (brightness, temperature, etc.)
    """
    import json
    trigger_time = parse_time_expression(time)

    params = {}
    if parameters:
        try:
            params = json.loads(parameters)
        except json.JSONDecodeError:
            pass

    action_dict = {
        "device_type": device_type,
        "room": room,
        "action": action,
        **params
    }

    task = schedule_manager.create_task(
        task_type="device_control",
        trigger_time=trigger_time,
        description=description,
        repeat=repeat,
        action=action_dict,
    )
    time_str = trigger_time.strftime("%Y-%m-%d %H:%M")
    repeat_info = f" (repeats {repeat})" if repeat != "once" else ""
    return ToolResponse(
        content=f"Scheduled: {description} at {time_str}{repeat_info} [ID: {task.id}]"
    )


def list_schedules() -> ToolResponse:
    """
    List all pending scheduled tasks and reminders.
    """
    tasks = schedule_manager.get_pending_tasks()
    if not tasks:
        return ToolResponse(content="No scheduled tasks or reminders.")

    lines = ["Scheduled tasks:"]
    for task in sorted(tasks, key=lambda t: t.trigger_time):
        time_str = task.trigger_time.strftime("%m-%d %H:%M")
        repeat_str = f" [{task.repeat.value}]" if task.repeat.value != "once" else ""
        if task.task_type.value == "reminder":
            lines.append(f"- {time_str}{repeat_str}: Reminder - {task.message} (ID: {task.id})")
        else:
            lines.append(f"- {time_str}{repeat_str}: {task.description} (ID: {task.id})")
    return ToolResponse(content="\n".join(lines))


def cancel_schedule(task_id: str) -> ToolResponse:
    """
    Cancel a scheduled task or reminder.

    Args:
        task_id: The ID of the task to cancel
    """
    task = schedule_manager.get_task(task_id)
    if not task:
        return ToolResponse(content=f"Task {task_id} not found.")

    if schedule_manager.cancel_task(task_id):
        return ToolResponse(content=f"Cancelled: {task.description}")
    return ToolResponse(content=f"Failed to cancel task {task_id}.")


def get_schedule_context() -> ToolResponse:
    """
    Get the current schedule context for display.
    """
    return ToolResponse(content=schedule_manager.get_context())
