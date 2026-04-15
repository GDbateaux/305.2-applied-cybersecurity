from ddgs import DDGS
from langchain_core.tools import tool


@tool
def search_internet(query: str) -> str:
    """Search for information online.
    Use this ONLY if search_kdrive + read_kdrive_file return no relevant results.
    Parameter: query (keywords to search for)."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "No results found. Try different keywords."
        # Format results for the LLM
        formatted = []
        for r in results:
            formatted.append(f"Title: {r.get('title', '')}\nURL: {r.get('href', '')}\nSummary: {r.get('body', '')}")
        return "\n\n".join(formatted)
    except Exception as e:
        return f"Search error: {e}"