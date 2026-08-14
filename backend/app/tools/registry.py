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
    local_tools = [calculator, rag_tool, web_search_tool]
    
    return local_tools


from langchain_core.runnables import RunnableConfig

@tool
def rag_tool(query: str, config: RunnableConfig) -> dict:
    """
    Retrieve relevant information from the knowledge base for this chat thread.
    Use this tool when the user asks a factual question that you don't know the answer to, 
    or when they ask about their uploaded documents.
    """
    from app.services.rag_service import query_knowledge_base
    
    user_id = config.get("configurable", {}).get("user_id")
    chat_filters = config.get("configurable", {}).get("filters", {})
    document_id = chat_filters.get("document_id") if chat_filters else None
    
    filters = {"user_id": user_id}
    if document_id:
        filters["document_id"] = document_id
    
    try:
        res = query_knowledge_base(query, filters=filters)
        return {
            "context": [source["content"] for source in res["sources"]],
            "sources": [{"filename": source["source"], "page": source["page"]} for source in res["sources"]]
        }
    except Exception as e:
        return {"error": str(e)}

