"""
Butler Agent - The main supervisor that understands user intent and delegates to sub-agents.
"""
import json
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import Msg

from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME
from agents.device_agent import DeviceControlAgent
from agents.scheduler_agent import SchedulerAgent
from core.state_manager import state_manager
from core.schedule_manager import schedule_manager


class ButlerAgent:
    """
    Butler is the main supervisor agent that:
    1. Understands user intent
    2. Routes tasks to appropriate sub-agents
    3. Aggregates responses and replies to user
    """

    def __init__(self):
        self.device_agent = DeviceControlAgent()
        self.scheduler_agent = SchedulerAgent()
        self.toolkit = Toolkit()
        self._register_tools()
        self.agent = self._create_agent()

    def _register_tools(self):
        """Register sub-agent dispatch tools."""
        self.toolkit.register_tool_function(self._dispatch_device_control)
        self.toolkit.register_tool_function(self._dispatch_scheduler)

    def _dispatch_device_control(
        self,
        task: str,
        device_type: str = None,
        room: str = None,
        action: str = None,
        parameters: str = None
    ) -> ToolResponse:
        """
        Dispatch a device control task to the Device Control Agent.

        Args:
            task: Natural language description of what to do (e.g., "turn on bedroom light")
            device_type: Type of device - light, ac, or speaker (optional, agent will infer)
            room: Room name (optional, agent will infer from task)
            action: Specific action like turn_on, turn_off, dim, set_temp (optional)
            parameters: JSON string of additional parameters like brightness, temperature (optional)

        Returns:
            Result of the device control operation
        """
        # Parse parameters if provided
        params = {}
        if parameters:
            try:
                params = json.loads(parameters)
            except json.JSONDecodeError:
                pass

        result = self.device_agent.execute(
            task=task,
            device_type=device_type,
            room=room,
            action=action,
            **params
        )
        return ToolResponse(content=result)

    def _dispatch_scheduler(
        self,
        task: str,
        action_type: str = None
    ) -> ToolResponse:
        """
        Dispatch a scheduling task to the Scheduler Agent.

        Args:
            task: Natural language description (e.g., "remind me to call mom in 30 minutes")
            action_type: Type hint - "reminder", "device_schedule", "list", or "cancel"

        Returns:
            Result of the scheduling operation
        """
        result = self.scheduler_agent.execute(
            task=task,
            action_type=action_type,
        )
        return ToolResponse(content=result)

    def _create_agent(self) -> ReActAgent:
        model = OpenAIChatModel(
            model_name=MODEL_NAME,
            api_key=OPENAI_API_KEY,
            client_args={"base_url": OPENAI_BASE_URL},
            stream=False,
        )
        return ReActAgent(
            name="Butler",
            sys_prompt=self._build_prompt(),
            model=model,
            formatter=OpenAIChatFormatter(),
            toolkit=self.toolkit,
            memory=InMemoryMemory(),
            parallel_tool_calls=True,
        )

    def _build_prompt(self) -> str:
        device_ctx = state_manager.get_context()
        schedule_ctx = schedule_manager.get_context()
        return f"""You are Butler, a smart home assistant supervisor.

{device_ctx}

{schedule_ctx}

Your role is to:
1. Understand user requests about their smart home
2. Delegate tasks to specialized sub-agents using the available tools
3. Provide friendly, helpful responses
4. Answer questions about current device status or schedules directly from the context above

Available sub-agents:
- Device Control Agent: Handles all device operations (lights, AC, speakers)
  Use `_dispatch_device_control` to send tasks to this agent
- Scheduler Agent: Handles reminders, scheduled tasks, and timed device control
  Use `_dispatch_scheduler` to send tasks to this agent

Guidelines:
- For questions about current device status, answer directly from the context
- For questions about schedules/reminders, answer directly from the context
- For device control requests (turn on/off lights, adjust AC, play music), use the device control dispatch tool
- For scheduling requests (reminders, timed actions, "every day at X"), use the scheduler dispatch tool
- Parse user intent and provide clear task descriptions to sub-agents
- Respond naturally in the same language as the user
- Be concise but friendly

Examples:
- "Turn on the bedroom light" → dispatch to device agent
- "Set AC to 22 degrees" → dispatch to device agent
- "Remind me to call mom in 30 minutes" → dispatch to scheduler with action_type="reminder"
- "Turn on lights every day at 7am" → dispatch to scheduler with action_type="device_schedule"
- "What's scheduled?" → answer directly from schedule context, or dispatch to scheduler with action_type="list"
- "Cancel reminder xxx" → dispatch to scheduler with action_type="cancel"
"""

    async def chat(self, user_input: str) -> str:
        # Update prompt with latest device state
        self.agent._sys_prompt = self._build_prompt()
        msg = Msg(name="user", content=user_input, role="user")
        response = await self.agent(msg)

        if hasattr(response, 'get_text_content'):
            return response.get_text_content()
        elif hasattr(response, 'content'):
            return response.content
        return str(response)

    def chat_sync(self, user_input: str) -> str:
        import asyncio
        return asyncio.run(self.chat(user_input))

    def clear_memory(self):
        self.agent.memory = InMemoryMemory()
        self.device_agent.clear_memory()
        self.scheduler_agent.clear_memory()
