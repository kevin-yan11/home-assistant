"""
Device Control Agent - Handles all smart home device operations.
"""
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit
from agentscope.message import Msg

from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME
from core.state_manager import state_manager
from tools.device_tools import control_light, control_ac, control_speaker, get_device_status


class DeviceControlAgent:
    """
    Sub-agent responsible for executing device control commands.
    Receives tasks from Butler and operates devices using tools.
    """

    def __init__(self):
        self.toolkit = Toolkit()
        self._register_tools()
        self.agent = self._create_agent()

    def _register_tools(self):
        """Register device control tools."""
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
            name="DeviceController",
            sys_prompt=self._build_prompt(),
            model=model,
            formatter=OpenAIChatFormatter(),
            toolkit=self.toolkit,
            memory=InMemoryMemory(),
            parallel_tool_calls=True,
        )

    def _build_prompt(self) -> str:
        ctx = state_manager.get_context()
        return f"""You are a Device Control Agent for a smart home system.

Your job is to execute device control commands using the available tools.

{ctx}

Available devices:
- Lights: bedroom, living_room (actions: turn_on, turn_off, dim)
- AC: bedroom, living_room (actions: turn_on, turn_off, set_temp)
- Speaker: living_room (actions: play, pause, stop, set_volume)

Guidelines:
- Use the appropriate tool function based on device type
- For lights: use control_light
- For AC: use control_ac
- For speakers: use control_speaker
- To check status: use get_device_status
- Return a brief confirmation of what was done
- Handle room name aliases (e.g., "卧室" = "bedroom", "客厅" = "living_room")
"""

    def execute(
        self,
        task: str,
        device_type: str = None,
        room: str = None,
        action: str = None,
        **kwargs
    ) -> str:
        """
        Execute a device control task.

        Args:
            task: Natural language task description
            device_type: Optional device type hint
            room: Optional room hint
            action: Optional action hint
            **kwargs: Additional parameters (brightness, temperature, etc.)
        """
        # Refresh prompt with latest device state
        self.agent._sys_prompt = self._build_prompt()

        # Build context message for the agent
        context_parts = [f"Task: {task}"]
        if device_type:
            context_parts.append(f"Device type: {device_type}")
        if room:
            context_parts.append(f"Room: {room}")
        if action:
            context_parts.append(f"Action: {action}")
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
