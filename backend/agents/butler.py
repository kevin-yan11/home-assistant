"""
Butler Agent - Hybrid routing: direct tool calls for simple tasks, sub-agents for complex ones.
"""
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import Msg

from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME
from agents.scheduler_agent import SchedulerAgent
from agents.search_agent import SearchAgent
from core.state_manager import state_manager
from core.schedule_manager import schedule_manager
from tools.device_tools import control_light, control_ac, control_speaker, get_device_status


class ButlerAgent:
    """
    Butler is a hybrid router that:
    1. Handles simple device control directly via tools (faster)
    2. Routes complex tasks (scheduling, search) to specialized sub-agents
    """

    def __init__(self):
        self.scheduler_agent = SchedulerAgent()
        self.search_agent = SearchAgent()
        self.toolkit = Toolkit()
        self._register_tools()
        self.agent = self._create_agent()

    def _register_tools(self):
        """Register direct tools and sub-agent dispatch tools."""
        # Direct device control tools (simple, fast path)
        self.toolkit.register_tool_function(control_light)
        self.toolkit.register_tool_function(control_ac)
        self.toolkit.register_tool_function(control_speaker)
        self.toolkit.register_tool_function(get_device_status)
        # Sub-agent dispatch tools (complex tasks)
        self.toolkit.register_tool_function(self._dispatch_scheduler)
        self.toolkit.register_tool_function(self._dispatch_search)

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

    def _dispatch_search(
        self,
        query: str
    ) -> ToolResponse:
        """
        Dispatch a search query to the Search Agent.

        Args:
            query: The search query or question (e.g., "weather in Beijing", "latest tech news")

        Returns:
            Search results summary
        """
        result = self.search_agent.execute(query=query)
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
        return f"""You are Butler, a smart home assistant.

{device_ctx}

{schedule_ctx}

Your role is to:
1. Understand user requests about their smart home
2. Execute simple device commands directly using tools
3. Delegate complex tasks (scheduling, search) to specialized sub-agents
4. Provide friendly, helpful responses

Available tools:
- Direct Device Control (fast, for simple commands):
  - `control_light`: Turn on/off lights, adjust brightness
  - `control_ac`: Turn on/off AC, set temperature
  - `control_speaker`: Play/pause/stop music, adjust volume
  - `get_device_status`: Check current device status

- Sub-agent Dispatch (for complex tasks):
  - `_dispatch_scheduler`: Reminders, scheduled tasks, timed device control
  - `_dispatch_search`: Web searches, weather, news, general questions

Guidelines:
- For simple device commands (turn on/off, adjust settings), use direct tools
- For questions about current device status, answer directly from the context above
- For questions about schedules/reminders, answer directly from the context above
- For scheduling requests (reminders, timed actions, "every day at X"), use `_dispatch_scheduler`
- For information queries (weather, news, general questions), use `_dispatch_search`
- Respond naturally in the same language as the user
- Be concise but friendly

Handling ambiguous/comfort requests:
When users express comfort issues without specific commands, analyze the device context and infer the appropriate action:
- "太暗了" / "It's too dark" → Check current light status, turn on lights or increase brightness
- "太亮了" / "It's too bright" → Decrease brightness or turn off lights
- "太冷了" / "It's too cold" → If AC is on cooling, raise temperature or turn off; if AC is off, turn on heating
- "太热了" / "It's too hot" → If AC is off, turn on cooling; if AC is on, lower temperature
- "太吵了" / "It's too loud" → Lower speaker volume or pause playback
- "太安静了" / "It's too quiet" → Play music or increase volume
Always consider the current device state before deciding. If unsure which room, ask the user or apply to all relevant rooms.

Examples:
- "Turn on the bedroom light" → use `control_light` directly
- "Set AC to 22 degrees" → use `control_ac` directly
- "太暗了" → check lights in context, if brightness is low, increase it or turn on
- "有点冷" → check AC status, if cooling at 22°C, raise to 24-25°C
- "What's the living room AC status?" → answer from context or use `get_device_status`
- "Remind me to call mom in 30 minutes" → `_dispatch_scheduler` with action_type="reminder"
- "Turn on lights every day at 7am" → `_dispatch_scheduler` with action_type="device_schedule"
- "What's scheduled?" → answer from schedule context
- "What's the weather today?" → `_dispatch_search`
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
        self.scheduler_agent.clear_memory()
        self.search_agent.clear_memory()
