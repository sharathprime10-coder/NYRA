from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import shutil

from app.db.database import get_db
from app.db.models.user import User
from app.db.models.document import Document
from app.core.security import get_current_user
from app.services.rag_service import process_and_store_document

router = APIRouter()

UPLOAD_DIR = "./uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def process_doc_task(file_path: str, document_id: int, db: Session):
    try:
        # Process and store in ChromaDB
        chunks = process_and_store_document(file_path, document_id)
        
        # Update document status
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            if chunks == 0:
                doc.status = "failed"
            else:
                doc.status = "ready"
            db.commit()
    except Exception as e:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "failed"
            db.commit()
        print(f"Error processing document: {e}")

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # 1. Save file locally
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Create DB entry
        db_doc = Document(filename=file.filename, status="processing", user_id=current_user.id)
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        # 3. Schedule background processing for RAG
        background_tasks.add_task(process_doc_task, file_path, db_doc.id, db)
        
        return {"message": "File uploaded and processing started", "document_id": db_doc.id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
def list_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    return docs

@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        # 1. Delete from DB
        doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # 2. Try to remove the physical file
        file_path = os.path.join(UPLOAD_DIR, doc.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # 3. Try to remove from ChromaDB
        from app.services.rag_service import delete_document_from_index
        delete_document_from_index(document_id)
        
        # 4. Remove from DB
        db.delete(doc)
        db.commit()
        return {"message": "Document deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
