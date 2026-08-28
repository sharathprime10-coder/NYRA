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
    import logging

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

    # --- Build filters and query with dual-type fallback ---
    # ChromaDB metadata is strictly typed. Legacy documents may have document_id/user_id
    # stored as int instead of str. We try str first, then fall back to int if no results.

    def _build_filters(uid, did):
        """Build ChromaDB filter dict from uid and did values."""
        if did is not None:
            return {"$and": [{"user_id": uid}, {"document_id": did}]}
        else:
            return {"user_id": uid}

    def _clean_filters(filters):
        """Remove None values that would crash ChromaDB."""
        clean = {}
        if "$and" in filters:
            valid = [c for c in filters["$and"] if list(c.values())[0] is not None]
            if len(valid) > 1:
                clean["$and"] = valid
            elif len(valid) == 1:
                clean = valid[0]
        else:
            clean = {k: v for k, v in filters.items() if v is not None}
        return clean

    def _try_query(uid_val, did_val, label):
        """Run a query with given uid/did values and return (result, sources_count)."""
        filters = _clean_filters(_build_filters(uid_val, did_val))
        res = query_knowledge_base(query, filters=filters)
        count = len(res.get("sources", []))
        logging.info(
            "rag_filter_attempt",
            extra={
                "event": "rag_filter_attempt",
                "filter_label": label,
                "user_id_value": str(uid_val),
                "user_id_type": type(uid_val).__name__,
                "document_id_value": str(did_val) if did_val is not None else "None",
                "document_id_type": type(did_val).__name__ if did_val is not None else "None",
                "chunks_found": count,
            },
        )
        return res, count

    try:
        # Attempt 1: str types (the expected/correct format)
        str_uid = str(user_id)
        str_did = str(document_id) if document_id is not None else None
        res, count = _try_query(str_uid, str_did, "str_primary")

        # Attempt 2: int fallback for legacy docs (both user_id and document_id)
        if count == 0:
            try:
                int_uid = int(user_id)
                int_did = int(document_id) if document_id is not None else None
                res, count = _try_query(int_uid, int_did, "int_fallback")
            except (ValueError, TypeError):
                # user_id or document_id can't be cast to int — skip fallback
                pass

        # If still zero results after both attempts, return explicit non-retryable error
        if count == 0:
            logging.warning(
                "rag_no_results",
                extra={
                    "event": "rag_no_results",
                    "user_id": str(user_id),
                    "document_id": str(document_id) if document_id else "None",
                },
            )
            return {
                "error": "No relevant documents found in the database. Do NOT retry your search."
            }

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
