import asyncio
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models.chat import ChatMessage, ChatSession
from app.db.models.user import User

router = APIRouter()


class ChatMessageRequest(BaseModel):
    message: str
    session_id: str | None = None
    filters: dict | None = None
    thinking_level: str = "low"
    force_refresh: bool = False
    tone: Literal["default", "sassy"] = "default"
    stream: bool = True


class Source(BaseModel):
    document_id: str | None
    source: str | None
    page: int | None
    content: str


class ChatMessageResponse(BaseModel):
    answer: str
    sources: list[Source]
    confidence: str
    session_id: str | None


@router.post("/")
@limiter.limit("60/minute")
async def send_message(
    request: Request,
    chat_request: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from langchain_core.messages import (
        AIMessage,
        HumanMessage,
        SystemMessage,
    )

    from app.db.models.chat import ChatMessage
    from app.graph.graph import nyra_graph
    from app.services.cache_service import get_cached_response, set_cached_response

    # Get or create session
    session_id = chat_request.session_id
    if session_id:
        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == session_id, ChatSession.user_id == current_user.id
            )
            .first()
        )
        if not session:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this session"
            )
    else:
        user_sessions = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == current_user.id)
            .order_by(ChatSession.created_at.desc())
            .all()
        )
        if len(user_sessions) >= 10:
            for session_to_delete in user_sessions[9:]:
                db.delete(session_to_delete)
            db.commit()

        new_session = ChatSession(user_id=current_user.id, title="NYRA Chat")
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        session_id = str(new_session.id)

    # Extract clean message without hidden system instructions
    clean_msg = chat_request.message.split("[System Instruction:")[0].strip()

    thinking_level = chat_request.thinking_level
    if thinking_level == "low":
        msg_lower = clean_msg.lower()
        needs_deep = any(
            kw in msg_lower
            for kw in ["calculate", "compare", "according to", "explain", "analyze"]
        )
        if len(clean_msg) > 100 or needs_deep:
            thinking_level = "medium"

    doc_id = chat_request.filters.get("document_id") if chat_request.filters else None
    
    # Chroma metadata stores document_id as a string, but the frontend sends it as a number.
    # We must cast it to a string here so the RAG filter matches.
    if chat_request.filters and doc_id is not None:
        chat_request.filters["document_id"] = str(doc_id)
        doc_id = str(doc_id)

    # Parallelize DB history load and Cache check
    def fetch_history():
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )

    def check_cache():
        if chat_request.force_refresh:
            return None
        return get_cached_response(chat_request.message, current_user.id, doc_id)

    history, cached = await asyncio.gather(
        asyncio.to_thread(fetch_history), asyncio.to_thread(check_cache)
    )

    if cached:
        db_ai_msg = ChatMessage(
            session_id=session_id,
            role="ai",
            content=cached["answer"],
            sources=json.dumps(cached["sources"]) if cached.get("sources") else None,
        )
        db.add(db_ai_msg)
        db.commit()

        if not chat_request.stream:
            return ChatMessageResponse(
                answer=cached["answer"],
                sources=cached["sources"] if cached.get("sources") else [],
                confidence=cached.get("confidence", "High"),
                session_id=str(session_id),
            )

        async def cached_stream():
            yield f"data: {json.dumps({'event': 'token', 'content': cached['answer']})}\n\n"
            yield f"data: {json.dumps({'event': 'end', 'session_id': session_id})}\n\n"

        return StreamingResponse(cached_stream(), media_type="text/event-stream")

    # ── SIMPLE-QUERY FAST-PATH ──────────────────────────────────────────
    # If thinking_level is "low", no document filter, and the message is
    # short, skip the entire multi-agent graph and answer with a single
    # fast Gemini call. This cuts 3-4 LLM calls down to 1.
    is_simple = thinking_level == "low" and not doc_id and len(clean_msg) < 200

    if is_simple:
        import logging as _log

        from app.core.llm_factory import get_fast_llm

        fast_llm = get_fast_llm()

        # Build a minimal prompt with recent history for context
        fast_messages = []
        for msg in history[-4:]:
            if msg.role == "user":
                fast_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "ai":
                fast_messages.append(AIMessage(content=msg.content))
        fast_messages.append(
            SystemMessage(
                content=(
                    "You are NYRA, a helpful and accurate AI assistant. "
                    "Answer the user's question concisely and directly. "
                    "Use markdown formatting."
                )
            )
        )
        fast_messages.append(HumanMessage(content=chat_request.message))

        # Save user message
        db_user_msg = ChatMessage(
            session_id=session_id, role="user", content=chat_request.message
        )
        db.add(db_user_msg)
        db.commit()

        _log.getLogger(__name__).info(
            "fast_path_activated",
            extra={"session_id": session_id, "msg_len": len(chat_request.message)},
        )

        if not chat_request.stream:
            # JSON response mode (voice orb)
            try:
                response = await fast_llm.ainvoke(fast_messages)
                answer = response.content
            except Exception:
                _log.getLogger(__name__).error(
                    "fast_path_failed", extra={"session_id": session_id}, exc_info=True
                )
                raise HTTPException(status_code=500, detail="An error occurred.")

            db_ai_msg = ChatMessage(
                session_id=session_id, role="ai", content=answer, sources=None
            )
            db.add(db_ai_msg)
            db.commit()
            set_cached_response(
                chat_request.message,
                str(current_user.id),
                doc_id,
                {"answer": answer, "sources": [], "confidence": "High"},
            )
            return ChatMessageResponse(
                answer=answer,
                sources=[],
                confidence="High",
                session_id=str(session_id),
            )

        # SSE streaming mode (chat UI)
        async def fast_stream():
            full_answer = ""
            try:
                yield f"data: {json.dumps({'event': 'status', 'node': 'writer'})}\n\n"
                async for chunk in fast_llm.astream(fast_messages):
                    token = chunk.content
                    if isinstance(token, str) and token:
                        full_answer += token
                        yield f"data: {json.dumps({'event': 'token', 'content': token})}\n\n"

                # Save to DB + cache
                def _save():
                    db_ai = ChatMessage(
                        session_id=session_id,
                        role="ai",
                        content=full_answer,
                        sources=None,
                    )
                    db.add(db_ai)
                    db.commit()
                    set_cached_response(
                        chat_request.message,
                        str(current_user.id),
                        doc_id,
                        {"answer": full_answer, "sources": [], "confidence": "High"},
                    )

                await asyncio.to_thread(_save)
                yield f"data: {json.dumps({'event': 'end', 'session_id': session_id})}\n\n"
            except Exception:
                _log.getLogger(__name__).error(
                    "fast_path_stream_failed",
                    extra={"session_id": session_id},
                    exc_info=True,
                )
                yield f"data: {json.dumps({'event': 'error', 'content': 'An error occurred.'})}\n\n"

        return StreamingResponse(fast_stream(), media_type="text/event-stream")

    # ── END FAST-PATH ─────────────────────────────────────────────────

    input_messages = []

    if len(history) > 6:
        older_history = history[:-6]
        recent_history = history[-6:]

        summary_prompt = "Summarize the following conversation history briefly:\n"
        for msg in older_history:
            summary_prompt += f"{msg.role.upper()}: {msg.content}\n"

        from app.core.llm_factory import get_router_llm

        try:
            summary = get_router_llm().invoke(summary_prompt).content
            input_messages.append(
                SystemMessage(content=f"Previous Conversation Summary: {summary}")
            )
        except Exception:
            pass

        history_to_process = recent_history
    else:
        history_to_process = history

    for msg in history_to_process:
        if msg.role == "user":
            input_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "ai":
            input_messages.append(AIMessage(content=msg.content))

    if doc_id:
        from app.db.models.document import Document

        doc = (
            db.query(Document)
            .filter(Document.id == doc_id, Document.user_id == current_user.id)
            .first()
        )
        if doc:
            sys_msg = SystemMessage(
                content=f"Context: The user has attached a document named '{doc.filename}' for this specific query. If the user refers to 'this document', 'the PDF', or similar, they are referring to '{doc.filename}'. You MUST use the rag_tool with query='{chat_request.message}' to retrieve and read the document content before answering."
            )
            input_messages.append(sys_msg)

    input_messages.append(HumanMessage(content=chat_request.message))

    db_user_msg = ChatMessage(
        session_id=session_id, role="user", content=chat_request.message
    )
    db.add(db_user_msg)
    db.commit()

    from app.core.token_tracker import TokenTrackerCallback

    config = {
        "configurable": {
            "thread_id": str(session_id),
            "filters": chat_request.filters,
            "thinking_level": thinking_level,
            "user_id": str(current_user.id),
            "tone": chat_request.tone,
        },
        "callbacks": [TokenTrackerCallback(str(session_id), "llm_invocation")],
    }

    if not chat_request.stream:
        final_answer = ""
        try:
            async for event in nyra_graph.astream_events(
                {"messages": input_messages, "user_id": str(current_user.id)},
                config=config,
                version="v2",
            ):
                kind = event["event"]
                if kind == "on_chat_model_stream" and "writer" in event.get("tags", []):
                    chunk = event["data"]["chunk"].content
                    if isinstance(chunk, str) and chunk:
                        final_answer += chunk
        except Exception:
            from app.core.logging_config import setup_logging

            logger = setup_logging()
            logger.error(
                "chat_pipeline_failed", extra={"session_id": session_id}, exc_info=True
            )
            raise HTTPException(
                status_code=500, detail="An error occurred during generation."
            )

        def save_final_sync():
            db_ai_msg = ChatMessage(
                session_id=session_id, role="ai", content=final_answer, sources=None
            )
            db.add(db_ai_msg)
            db.commit()
            set_cached_response(
                chat_request.message,
                str(current_user.id),
                doc_id,
                {
                    "answer": final_answer,
                    "sources": [],
                    "confidence": "High",
                },
            )

        await asyncio.to_thread(save_final_sync)
        return ChatMessageResponse(
            answer=final_answer,
            sources=[],
            confidence="High",
            session_id=str(session_id),
        )

    async def event_generator():
        final_answer = ""
        try:
            async for event in nyra_graph.astream_events(
                {"messages": input_messages, "user_id": str(current_user.id)},
                config=config,
                version="v2",
            ):
                kind = event["event"]
                name = event.get("name", "")

                # Report node transitions
                if kind == "on_chain_start" and name in [
                    "supervisor",
                    "researcher",
                    "writer",
                    "critic",
                ]:
                    if name == "writer":
                        final_answer = ""
                        yield f"data: {json.dumps({'event': 'clear'})}\n\n"
                    yield f"data: {json.dumps({'event': 'status', 'node': name})}\n\n"

                # Stream writer node output
                elif kind == "on_chat_model_stream" and "writer" in event.get(
                    "tags", []
                ):
                    chunk = event["data"]["chunk"].content
                    chunk_text = ""
                    if isinstance(chunk, str) and chunk:
                        chunk_text = chunk
                    elif isinstance(chunk, list):
                        for item in chunk:
                            if isinstance(item, dict) and "text" in item:
                                chunk_text += item["text"]
                            elif isinstance(item, str):
                                chunk_text += item

                    if chunk_text:
                        final_answer += chunk_text
                        yield f"data: {json.dumps({'event': 'token', 'content': chunk_text})}\n\n"

            # Save final message
            def save_final():
                db_ai_msg = ChatMessage(
                    session_id=session_id, role="ai", content=final_answer, sources=None
                )
                db.add(db_ai_msg)
                db.commit()
                # Cache
                set_cached_response(
                    chat_request.message,
                    str(current_user.id),
                    doc_id,
                    {
                        "answer": final_answer,
                        "sources": [],
                        "confidence": "High",
                    },
                )

            await asyncio.to_thread(save_final)

            yield f"data: {json.dumps({'event': 'end', 'session_id': session_id})}\n\n"

        except Exception:
            from app.core.logging_config import setup_logging

            logger = setup_logging()
            logger.error(
                "chat_pipeline_failed", extra={"session_id": session_id}, exc_info=True
            )
            yield f"data: {json.dumps({'event': 'error', 'content': 'An error occurred during generation.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/history")
def get_chat_history(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )

    result = []
    for s in sessions:
        msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == str(s.id))
            .order_by(ChatMessage.created_at)
            .all()
        )
        if msgs:
            result.append(
                {
                    "id": str(s.id),
                    "title": s.title,
                    "created_at": s.created_at.isoformat(),
                    "message_count": len(msgs),
                }
            )

    return result


@router.get("/{session_id}")
def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.db.models.chat import ChatMessage

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "sources": json.loads(msg.sources) if msg.sources else [],
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]


@router.delete("/{session_id}")
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()
    return {"status": "success"}
