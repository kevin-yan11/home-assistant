import asyncio
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit
from agentscope.message import Msg

from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME
from core.state_manager import state_manager
from tools.device_tools import control_light, control_ac, control_speaker, get_device_status


class HomeAssistant:
    def __init__(self):
        self.toolkit = Toolkit()
        self._register_tools()
        self.agent = self._create_agent()

    def _register_tools(self):
        self.toolkit.register_tool_function(control_light)
        self.toolkit.register_tool_function(control_ac)
        self.toolkit.register_tool_function(control_speaker)
        self.toolkit.register_tool_function(get_device_status)

    def _create_agent(self) -> ReActAgent:
        model = OpenAIChatModel(
            model_name=MODEL_NAME,
            api_key=OPENAI_API_KEY,
            client_args={"base_url": OPENAI_BASE_URL},
            stream=False,
        )
        return ReActAgent(
            name="HomeAssistant",
            sys_prompt=self._build_prompt(),
            model=model,
            formatter=OpenAIChatFormatter(),
            toolkit=self.toolkit,
            memory=InMemoryMemory(),
            parallel_tool_calls=True,
        )

    def _build_prompt(self) -> str:
        ctx = state_manager.get_context()
        return f"""You are a smart home assistant. Control lights, AC, and speakers based on user requests.

{ctx}

Guidelines:
- Use appropriate tool functions to execute device control
- Consider current device state when making adjustments
- Respond naturally in the same language as the user
- For relative commands like "brighter" or "warmer", adjust based on current values
"""

    async def chat(self, user_input: str) -> str:
        self.agent._sys_prompt = self._build_prompt()
        msg = Msg(name="user", content=user_input, role="user")
        response = await self.agent(msg)
        
        # Extract text content from response
        if hasattr(response, 'get_text_content'):
            return response.get_text_content()
        elif hasattr(response, 'content'):
            return response.content
        return str(response)

    def chat_sync(self, user_input: str) -> str:
        return asyncio.run(self.chat(user_input))

    def clear_memory(self):
        self.agent.memory = InMemoryMemory()
