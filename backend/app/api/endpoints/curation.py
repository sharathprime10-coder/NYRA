import os
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.db.database import get_db
from app.db.models.chat import SharedKnowledgeStaging
from app.services.rag_service import shared_vector_store
from langchain_core.documents import Document as LangchainDocument

router = APIRouter()

class OptInRequest(BaseModel):
    user_query: str
    ai_response: str

class StagingResponse(BaseModel):
    id: str
    user_query: str
    ai_response: str
    status: str
    created_at: str

def verify_admin(authorization: Optional[str] = Header(None)):
    """Simple admin verification using a hardcoded token or email check."""
    # For local/demo, we can check for a specific header or just allow it.
    # We'll allow it for now but add a basic check that can be configured.
    admin_token = os.environ.get("ADMIN_TOKEN")
    if admin_token and authorization != f"Bearer {admin_token}":
        raise HTTPException(status_code=403, detail="Not authorized as Admin")
    return True

@router.post("/opt-in")
def opt_in_knowledge(req: OptInRequest, db: Session = Depends(get_db)):
    """User opts in to share a Q&A pair."""
    staging = SharedKnowledgeStaging(
        user_query=req.user_query,
        ai_response=req.ai_response,
        status="pending"
    )
    db.add(staging)
    db.commit()
    return {"status": "success", "message": "Successfully submitted for review"}

@router.get("/pending", response_model=List[StagingResponse])
def get_pending_pairs(db: Session = Depends(get_db), _: bool = Depends(verify_admin)):
    """Admin endpoint to fetch pending Q&A pairs."""
    records = db.query(SharedKnowledgeStaging).filter(SharedKnowledgeStaging.status == "pending").all()
    return [
        StagingResponse(
            id=str(r.id),
            user_query=r.user_query,
            ai_response=r.ai_response,
            status=r.status,
            created_at=r.created_at.isoformat()
        ) for r in records
    ]

@router.post("/approve/{staging_id}")
def approve_pair(staging_id: str, db: Session = Depends(get_db), _: bool = Depends(verify_admin)):
    """Admin approves a pair. Adds it to ChromaDB."""
    record = db.query(SharedKnowledgeStaging).filter(SharedKnowledgeStaging.id == staging_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Staging record not found")
        
    if record.status != "pending":
        raise HTTPException(status_code=400, detail="Record is not pending")
        
    # Add to shared vector store
    combined_content = f"Q: {record.user_query}\nA: {record.ai_response}"
    doc = LangchainDocument(
        page_content=combined_content, 
        metadata={"source": "Shared NYRA Knowledge Base", "document_id": "shared_faq", "type": "qa_pair"}
    )
    shared_vector_store.add_documents([doc])
    
    # Update DB
    record.status = "approved"
    db.commit()
    return {"status": "success"}

@router.post("/reject/{staging_id}")
def reject_pair(staging_id: str, db: Session = Depends(get_db), _: bool = Depends(verify_admin)):
    """Admin rejects a pair."""
    record = db.query(SharedKnowledgeStaging).filter(SharedKnowledgeStaging.id == staging_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Staging record not found")
        
    record.status = "rejected"
    db.commit()
    return {"status": "success"}
