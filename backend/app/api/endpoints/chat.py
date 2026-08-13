from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.db.database import get_db
from app.db.models.user import User
from app.core.security import get_current_user
from app.services.rag_service import query_knowledge_base
from app.core.rate_limit import limiter

router = APIRouter()

class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    filters: Optional[dict] = None

class Source(BaseModel):
    document_id: Optional[int]
    source: Optional[str]
    page: Optional[int]
    content: str

class ChatMessageResponse(BaseModel):
    answer: str
    sources: List[Source]
    confidence: str
    session_id: Optional[int]

@router.post("/", response_model=ChatMessageResponse)
@limiter.limit("60/minute")
def send_message(
    request: Request, 
    chat_request: ChatMessageRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.graph.graph import nyra_graph
    from langchain_core.messages import HumanMessage, ToolMessage
    from app.db.models.chat import ChatSession, ChatMessage
    import json
    
    # Get or create session
    session_id = chat_request.session_id
    if not session_id:
        new_session = ChatSession(user_id=current_user.id, title="NYRA Chat")
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        session_id = new_session.id
    
    # Log user message to relational DB for frontend history
    db_user_msg = ChatMessage(
        session_id=session_id,
        role="user",
        content=chat_request.message
    )
    db.add(db_user_msg)
    db.commit()
        
    config = {"configurable": {"thread_id": str(session_id)}}
    
    try:
        # Run graph
        result = nyra_graph.invoke(
            {
                "messages": [HumanMessage(content=chat_request.message)],
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
                except Exception:
                    pass
        
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
            session_id=session_id
        )
    except Exception as e:
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
            except Exception:
                pass
                
        result.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "sources": sources_list,
            "created_at": msg.created_at
        })
        
    return result
