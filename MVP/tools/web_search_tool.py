from ddgs import DDGS

def web_search(query: str, max_results: int = 5):
    """
    USE THIS TOOL to find real-time information, news, or facts 
    from the internet that are not in your internal database.
    
    Args:
        query (str): The search keywords or question.
        max_results (int): Number of results to return.
        
    Returns:
        list: A list of results with 'title', 'href', and 'body'.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            
        if not results:
            return "Search yielded no results. Try broadening your keywords."
            
        return results
    except Exception as e:
        return f"Error during web search: {e}"

if __name__ == "__main__":
    print(web_search("Infomaniak kDrive API news 2026"))
