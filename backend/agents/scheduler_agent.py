"""
Scheduler Agent - Handles scheduled tasks and reminders.
"""
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit
from agentscope.message import Msg

from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME
from core.schedule_manager import schedule_manager
from tools.schedule_tools import (
    create_reminder,
    create_device_schedule,
    list_schedules,
    cancel_schedule,
    get_schedule_context,
)


class SchedulerAgent:
    """
    Sub-agent responsible for managing schedules, reminders, and timed device actions.
    """

    def __init__(self):
        self.toolkit = Toolkit()
        self._register_tools()
        self.agent = self._create_agent()

    def _register_tools(self):
        """Register schedule management tools."""
        self.toolkit.register_tool_function(create_reminder)
        self.toolkit.register_tool_function(create_device_schedule)
        self.toolkit.register_tool_function(list_schedules)
        self.toolkit.register_tool_function(cancel_schedule)
        self.toolkit.register_tool_function(get_schedule_context)

    def _create_agent(self) -> ReActAgent:
        model = OpenAIChatModel(
            model_name=MODEL_NAME,
            api_key=OPENAI_API_KEY,
            client_args={"base_url": OPENAI_BASE_URL},
            stream=False,
        )
        return ReActAgent(
            name="Scheduler",
            sys_prompt=self._build_prompt(),
            model=model,
            formatter=OpenAIChatFormatter(),
            toolkit=self.toolkit,
            memory=InMemoryMemory(),
            parallel_tool_calls=True,
        )

    def _build_prompt(self) -> str:
        ctx = schedule_manager.get_context()
        return f"""You are a Scheduler Agent for a smart home system.

Your job is to manage scheduled tasks, reminders, and timed device control actions.

{ctx}

Capabilities:
- Create reminders: "remind me to...", "set a reminder for..."
- Schedule device actions: "turn on light at 7am every day", "set AC to 24 at 6pm"
- List schedules: "what's scheduled?", "show my reminders"
- Cancel schedules: "cancel the reminder", "remove schedule xxx"

Time parsing:
- Relative: "in 10 minutes", "in 1 hour"
- Today: "today 14:00", "at 3pm"
- Tomorrow: "tomorrow 9:00", "tomorrow morning"
- Absolute: "2024-01-15 10:00"
- Time only: "07:00" (assumes today or next occurrence)

Repeat options:
- "once" (default): one-time task
- "daily": repeats every day
- "weekly": repeats every week

Guidelines:
- Parse user's natural language into specific time and action
- For device schedules, specify device_type, room, and action clearly
- Confirm what was scheduled with the exact time
- Return brief, clear confirmations
"""

    def execute(
        self,
        task: str,
        action_type: str = None,
        **kwargs
    ) -> str:
        """
        Execute a scheduling task.

        Args:
            task: Natural language task description
            action_type: Optional hint - "reminder", "device_schedule", "list", "cancel"
            **kwargs: Additional parameters
        """
        # Refresh prompt with latest schedule state
        self.agent._sys_prompt = self._build_prompt()

        # Build context message
        context_parts = [f"Task: {task}"]
        if action_type:
            context_parts.append(f"Action type: {action_type}")
        if kwargs:
            context_parts.append(f"Parameters: {kwargs}")

        message = "\n".join(context_parts)
        msg = Msg(name="butler", content=message, role="user")

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self._async_call(msg))
                    response = future.result()
            else:
                response = asyncio.run(self._async_call(msg))
        except RuntimeError:
            response = asyncio.run(self._async_call(msg))

        if hasattr(response, 'get_text_content'):
            return response.get_text_content()
        elif hasattr(response, 'content'):
            return response.content
        return str(response)

    async def _async_call(self, msg: Msg):
        return await self.agent(msg)

    def clear_memory(self):
        self.agent.memory = InMemoryMemory()
