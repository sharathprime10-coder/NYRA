from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

from app.db.database import get_db
from app.db.models.user import User
from app.core.security import get_current_user
from app.services.rag_service import query_knowledge_base
from app.core.rate_limit import limiter

router = APIRouter()

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[UUID] = None
    filters: Optional[dict] = None
    thinking_level: str = "medium"

class Source(BaseModel):
    document_id: Optional[str]
    source: Optional[str]
    page: Optional[int]
    content: str

class ChatMessageResponse(BaseModel):
    answer: str
    sources: List[Source]
    confidence: str
    session_id: Optional[str]

@router.post("/", response_model=ChatMessageResponse)
@limiter.limit("60/minute")
def send_message(
    request: Request, 
    chat_request: ChatMessageRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.graph.graph import nyra_graph
    from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, SystemMessage
    from app.db.models.chat import ChatSession, ChatMessage
    import json
    
    # Get or create session
    session_id = chat_request.session_id
    if session_id:
        # Verify the session belongs to the current user (BOLA/IDOR protection)
        session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
        if not session:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
    else:
        new_session = ChatSession(user_id=current_user.id, title="NYRA Chat")
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        session_id = new_session.id
    
    # Get message history
    history = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
    input_messages = []
    for msg in history:
        if msg.role == "user":
            input_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "ai":
            input_messages.append(AIMessage(content=msg.content))

    # Append new user message
    input_messages.append(HumanMessage(content=chat_request.message))
    
    # Log user message to relational DB for frontend history
    db_user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=chat_request.message
    )
    db.add(db_user_msg)
    db.commit()
    
    doc_id = chat_request.filters.get("document_id") if chat_request.filters else None
    if doc_id:
        from app.db.models.document import Document
        doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
        if doc:
            sys_msg = SystemMessage(content=f"Context: The user has attached a document named '{doc.filename}' for this specific query. If the user refers to 'this document', 'the PDF', or similar, they are referring to '{doc.filename}'. Use the rag_tool to read it.")
            input_messages.append(sys_msg)

    config = {
        "configurable": {
            "thread_id": str(session_id),
            "filters": chat_request.filters,
            "thinking_level": chat_request.thinking_level,
            "user_id": current_user.id
        }
    }
    
    try:
        # Run graph
        result = nyra_graph.invoke(
            {
                "messages": input_messages,
                "user_id": current_user.id
            }, 
            config=config
        )
        
        final_content = result["messages"][-1].content
        if isinstance(final_content, list):
            final_message = ""
            for block in final_content:
                if isinstance(block, dict) and "text" in block:
                    final_message += block["text"]
                elif isinstance(block, str):
                    final_message += block
        else:
            final_message = str(final_content)
        
        # Extract sources from RAG tool if it was used
        sources = []
        confidence = "High"
        for msg in result["messages"]:
            if getattr(msg, "name", None) == "rag_tool" and isinstance(msg, ToolMessage):
                try:
                    data = json.loads(msg.content)
                    if "sources" in data:
                        for src in data["sources"]:
                            sources.append(Source(
                                document_id=src.get("document_id"),
                                source=src.get("filename"),
                                page=src.get("page"),
                                content=""
                            ))
                except Exception as e:
                    import logging
                    logging.warning(f"Failed to parse tool message sources: {e}")
        
        # Log AI message to relational DB for frontend history
        db_ai_msg = ChatMessage(
            session_id=session_id,
            role="ai",
            content=final_message,
            sources=json.dumps([s.dict() for s in sources]) if sources else None
        )
        db.add(db_ai_msg)
        db.commit()
        
        return ChatMessageResponse(
            answer=final_message,
            sources=sources,
            confidence=confidence,
            session_id=str(session_id) if session_id else None
        )
    except Exception as e:
        import traceback
        with open("error_log.txt", "a") as f:
            f.write("ERROR IN CHAT API:\n")
            f.write(traceback.format_exc())
            f.write("\n\n")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
def get_chat_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.db.models.chat import ChatSession
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).order_by(ChatSession.created_at.desc()).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at} for s in sessions]

@router.get("/{session_id}")
def get_session_messages(session_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.db.models.chat import ChatSession, ChatMessage
    import json
    
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    
    result = []
    for msg in messages:
        sources_list = []
        if msg.sources:
            try:
                sources_list = json.loads(msg.sources)
            except Exception as e:
                import logging
                logging.warning(f"Failed to parse chat message sources: {e}")
                
        result.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "sources": sources_list,
            "created_at": msg.created_at
        })
        
    return result
