from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import List
import os
import shutil

from app.db.database import get_db, SessionLocal
from app.db.models.user import User
from app.db.models.document import Document
from app.core.security import get_current_user
from app.services.rag_service import process_and_store_document
from app.core.rate_limit import limiter

router = APIRouter()

UPLOAD_DIR = "./uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

from app.core.logging_config import setup_logging

logger = setup_logging()

def process_doc_task(file_path: str, document_id: str, user_id: str):
    db = SessionLocal()
    try:
        # Process and store in ChromaDB
        chunks = process_and_store_document(file_path, document_id, user_id)
        
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
    finally:
        db.close()

@router.post("/upload")
@limiter.limit("20/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # 0. Enforce 25MB file size limit
        file_content = await file.read()
        if len(file_content) > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 25MB.")
        await file.seek(0) # Reset file pointer for writing later

        # 1. Sanitize filename and validate extension
        safe_original_name = os.path.basename(file.filename)
        allowed_extensions = [".pdf", ".txt", ".md", ".csv", ".docx", ".mp3", ".wav", ".m4a"]
        audio_extensions = [".mp3", ".wav", ".m4a"]
        ext = os.path.splitext(safe_original_name)[1].lower()
        
        if ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"File type {ext} not allowed for security reasons.")
            
        # 2. Create DB entry with sanitized name
        initial_status = "transcribing" if ext in audio_extensions else "processing"
        db_doc = Document(filename=safe_original_name, status=initial_status, user_id=current_user.id)
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        
        # 3. Save file locally using a secure UUID and scoped to user_id to prevent Path Traversal and support MCP
        user_upload_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
        os.makedirs(user_upload_dir, exist_ok=True)
        
        safe_disk_filename = f"{db_doc.id}{ext}"
        file_path = os.path.join(user_upload_dir, safe_disk_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 4. Schedule background processing for RAG
        background_tasks.add_task(process_doc_task, file_path, str(db_doc.id), str(current_user.id))
        
        return {"message": "File uploaded and processing started", "document_id": db_doc.id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while uploading the document.")

@router.get("/")
def list_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    return docs

@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        # 1. Delete from DB
        doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # 2. Try to remove the physical file
        ext = os.path.splitext(doc.filename)[1].lower()
        user_upload_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
        file_path = os.path.join(user_upload_dir, f"{doc.id}{ext}")
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # 3. Try to remove from ChromaDB
        from app.services.rag_service import delete_document_from_index
        delete_document_from_index(str(document_id))
        
        # 4. Remove from DB
        db.delete(doc)
        db.commit()
        return {"message": "Document deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while deleting the document.")
