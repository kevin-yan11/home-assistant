"""
Search tools for querying external information using DuckDuckGo.
"""
from agentscope.tool import ToolResponse

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False


def web_search(query: str, max_results: int = 5) -> ToolResponse:
    """
    Search the web using DuckDuckGo.

    Args:
        query: The search query (e.g., "weather in Beijing", "latest news")
        max_results: Maximum number of results to return (default 5)

    Returns:
        Search results with titles, snippets, and URLs
    """
    if not DDGS_AVAILABLE:
        return ToolResponse(
            content="Search unavailable: duckduckgo-search package not installed. "
                    "Run: pip install duckduckgo-search"
        )

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return ToolResponse(content=f"No results found for: {query}")

        # Format results
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(
                f"{i}. {r.get('title', 'No title')}\n"
                f"   {r.get('body', 'No description')}\n"
                f"   URL: {r.get('href', 'No URL')}"
            )

        return ToolResponse(content="\n\n".join(formatted))

    except Exception as e:
        return ToolResponse(content=f"Search error: {str(e)}")


def search_news(query: str, max_results: int = 5) -> ToolResponse:
    """
    Search for news articles using DuckDuckGo.

    Args:
        query: The news search query (e.g., "technology news", "sports")
        max_results: Maximum number of results to return (default 5)

    Returns:
        News results with titles, dates, and snippets
    """
    if not DDGS_AVAILABLE:
        return ToolResponse(
            content="Search unavailable: duckduckgo-search package not installed."
        )

    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results))

        if not results:
            return ToolResponse(content=f"No news found for: {query}")

        formatted = []
        for i, r in enumerate(results, 1):
            date = r.get('date', 'Unknown date')
            formatted.append(
                f"{i}. [{date}] {r.get('title', 'No title')}\n"
                f"   {r.get('body', 'No description')}\n"
                f"   Source: {r.get('source', 'Unknown')}"
            )

        return ToolResponse(content="\n\n".join(formatted))

    except Exception as e:
        return ToolResponse(content=f"News search error: {str(e)}")
