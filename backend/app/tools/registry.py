from langchain_core.tools import BaseTool, tool


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


async def get_all_tools(user_id: int = None) -> list[BaseTool]:
    local_tools = [calculator, rag_tool, web_search_tool]

    from app.tools.mcp_client import get_mcp_tools

    if user_id is not None:
        mcp_tools = await get_mcp_tools(user_id)
        local_tools.extend(mcp_tools)

    return local_tools


from langchain_core.runnables import RunnableConfig


@tool
def rag_tool(query: str, config: RunnableConfig) -> dict:
    """
    Retrieve relevant information from the knowledge base for this chat thread.
    Use this tool when the user asks a factual question that you don't know the answer to,
    or when they ask about their uploaded documents.
    """
    from app.db.database import SessionLocal
    from app.db.models.document import Document
    from app.services.rag_service import query_knowledge_base

    user_id = config.get("configurable", {}).get("user_id")
    chat_filters = config.get("configurable", {}).get("filters", {})
    document_id = chat_filters.get("document_id") if chat_filters else None

    # GUARDRAIL: Verify the user owns this document before searching
    if not user_id:
        return {
            "error": "GUARDRAIL BLOCK: user_id is required to perform a knowledge base search."
        }

    if document_id and user_id:
        db = SessionLocal()
        try:
            doc = (
                db.query(Document)
                .filter(Document.id == document_id, Document.user_id == user_id)
                .first()
            )
            if not doc:
                return {
                    "error": "GUARDRAIL BLOCK: You do not have permission to access this document_id or it does not exist."
                }
        finally:
            db.close()

    if document_id:
        filters = {"$and": [{"user_id": str(user_id)}, {"document_id": str(document_id)}]}
    else:
        filters = {"user_id": str(user_id)}

    # ChromaDB crashes if where clauses contain None values
    clean_filters = {}
    if "$and" in filters:
        valid_conditions = [
            cond for cond in filters["$and"] if list(cond.values())[0] is not None
        ]
        if len(valid_conditions) > 1:
            clean_filters["$and"] = valid_conditions
        elif len(valid_conditions) == 1:
            clean_filters = valid_conditions[0]
    else:
        clean_filters = {k: v for k, v in filters.items() if v is not None}

    try:
        res = query_knowledge_base(query, filters=clean_filters)

        # Resolve document filenames from DB instead of showing raw file paths
        db = SessionLocal()
        try:
            resolved_sources = []
            seen_doc_ids = set()
            for source in res["sources"]:
                doc_id = source.get("document_id")

                # Deduplicate by document_id so the UI only shows each source once
                if doc_id in seen_doc_ids:
                    continue
                seen_doc_ids.add(doc_id)

                filename = source.get("source", "Unknown")
                if doc_id:
                    doc = db.query(Document).filter(Document.id == doc_id).first()
                    if doc:
                        filename = doc.filename
                resolved_sources.append(
                    {
                        "filename": filename,
                        "page": source.get("page"),
                        "document_id": doc_id,
                    }
                )
        finally:
            db.close()

        return {
            "context": [source["content"] for source in res["sources"]],
            "sources": resolved_sources,
            "confidence": res.get("confidence", "Medium"),
            "min_distance": res.get("min_distance", 1.0),
        }
    except Exception as e:
        return {"error": str(e)}
