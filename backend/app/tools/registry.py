from typing import List
from langchain_core.tools import tool, BaseTool

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}

        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result,
        }
    except Exception as e:
        return {"error": str(e)}

from langchain_community.tools import DuckDuckGoSearchRun

web_search_tool = DuckDuckGoSearchRun(region="us-en")

def get_all_tools() -> List[BaseTool]:
    """Returns a list of all tools registered in NYRA."""
    from app.tools.mcp_client import get_mcp_tools
    
    local_tools = [calculator, rag_tool, web_search_tool]
    mcp_tools = get_mcp_tools()
    
    return local_tools + mcp_tools


@tool
def rag_tool(query: str, thread_id: str = None) -> dict:
    """
    Retrieve relevant information from the knowledge base for this chat thread.
    Use this tool when the user asks a factual question that you don't know the answer to, 
    or when they ask about their uploaded documents.
    """
    from app.services.rag_service import query_knowledge_base
    
    # In a full multi-tenant system, we would filter by user_id or thread_id
    # For now, we just query the global knowledge base
    # e.g., filters = {"thread_id": thread_id}
    try:
        res = query_knowledge_base(query)
        return {
            "context": [source["content"] for source in res["sources"]],
            "sources": [{"filename": source["source"], "page": source["page"]} for source in res["sources"]]
        }
    except Exception as e:
        return {"error": str(e)}

