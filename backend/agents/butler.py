"""
Butler Agent - Single agent with direct tool access.
No sub-agents, flat architecture for simplicity and speed.
"""
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit
from agentscope.message import Msg

from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME
from core.state_manager import state_manager
from core.schedule_manager import schedule_manager
from core.rule_engine import rule_engine

# Import all tools directly
from tools.device_tools import control_light, control_ac, control_speaker, get_device_status
from tools.schedule_tools import create_reminder, create_device_schedule, list_schedules, cancel_schedule
from tools.search_tools import web_search, search_news


class ButlerAgent:
    """
    Butler is a single smart home assistant that:
    1. Understands user requests (commands, questions, ambiguous expressions)
    2. Calls tools directly to perform actions
    3. Responds naturally to the user
    """

    def __init__(self):
        self.toolkit = Toolkit()
        self._register_tools()
        self.agent = self._create_agent()

    def _register_tools(self):
        """Register all tools directly."""
        # Device control tools
        self.toolkit.register_tool_function(control_light)
        self.toolkit.register_tool_function(control_ac)
        self.toolkit.register_tool_function(control_speaker)
        self.toolkit.register_tool_function(get_device_status)
        # Schedule tools
        self.toolkit.register_tool_function(create_reminder)
        self.toolkit.register_tool_function(create_device_schedule)
        self.toolkit.register_tool_function(list_schedules)
        self.toolkit.register_tool_function(cancel_schedule)
        # Search tools
        self.toolkit.register_tool_function(web_search)
        self.toolkit.register_tool_function(search_news)

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

You have direct access to tools for device control, scheduling, and web search.

Available tools:
- Device Control:
  - control_light(room, action, brightness): Turn on/off lights, adjust brightness
  - control_ac(room, action, temperature, mode): Turn on/off AC, set temperature
  - control_speaker(room, action, volume): Play/pause/stop music, adjust volume
  - get_device_status(room, device_type): Check device status

- Scheduling:
  - create_reminder(message, time, repeat): Set reminders
  - create_device_schedule(description, time, device_type, room, action, repeat): Schedule device actions
  - list_schedules(): Show all scheduled tasks
  - cancel_schedule(task_id): Cancel a task

- Search:
  - web_search(query): Search the web
  - search_news(query): Search news articles

Guidelines:
- For device commands, call the appropriate control tool directly
- For status questions, check the context above first; use tools only if needed
- For reminders/schedules, use the scheduling tools
- For information queries (weather, news, questions), use search tools
- Handle ambiguous comfort requests by inferring the action:
  - "too dark" → turn on lights or increase brightness
  - "too cold" → raise AC temperature or turn on heating
  - "too hot" → lower AC temperature or turn on cooling
  - "too loud" → lower speaker volume
- Respond naturally in the same language as the user
- Be concise but friendly
"""

    async def chat(self, user_input: str) -> str:
        # Layer 1: Try rule engine first (fast path)
        rule_result = rule_engine.process(user_input)
        if rule_result.matched:
            return rule_result.response

        # Layer 2: Fall back to LLM agent
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
