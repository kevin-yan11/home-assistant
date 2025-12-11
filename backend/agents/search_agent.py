"""
Search Agent - Handles web searches and information queries.
"""
from agentscope.agent import ReActAgent
from agentscope.model import OpenAIChatModel
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.tool import Toolkit
from agentscope.message import Msg

from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME
from tools.search_tools import web_search, search_news


class SearchAgent:
    """
    Sub-agent responsible for searching the web and answering information queries.
    """

    def __init__(self):
        self.toolkit = Toolkit()
        self._register_tools()
        self.agent = self._create_agent()

    def _register_tools(self):
        """Register search tools."""
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
            name="SearchAgent",
            sys_prompt=self._build_prompt(),
            model=model,
            formatter=OpenAIChatFormatter(),
            toolkit=self.toolkit,
            memory=InMemoryMemory(),
            parallel_tool_calls=False,
        )

    def _build_prompt(self) -> str:
        return """You are a Search Agent for a smart home assistant.

Your job is to search the web and answer user questions about:
- Weather (current conditions, forecasts)
- News (current events, headlines)
- General knowledge questions
- Any other information the user asks about

Available tools:
- web_search: General web search for any query
- search_news: Search for recent news articles

Guidelines:
- Use web_search for weather, general questions, how-to queries
- Use search_news for current events, headlines, breaking news
- Summarize the search results in a clear, concise way
- Include relevant details like temperatures, dates, sources
- Respond in the same language as the user's query
- If search fails, apologize and suggest rephrasing the query

Examples:
- "What's the weather in Beijing?" → use web_search with "Beijing weather today"
- "Any tech news?" → use search_news with "technology news"
- "How to make coffee?" → use web_search with "how to make coffee"
"""

    def execute(self, query: str) -> str:
        """
        Execute a search query.

        Args:
            query: The search query or question

        Returns:
            Search results summary
        """
        msg = Msg(name="butler", content=f"Search query: {query}", role="user")

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
