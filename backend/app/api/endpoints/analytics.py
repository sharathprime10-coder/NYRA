
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.database import get_db
from app.db.models.chat import ChatMessage, ChatSession
from app.db.models.user import User

router = APIRouter()


class PromptRequest(BaseModel):
    message: str


@router.get("/session/{session_id}")
def get_session_analytics(
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

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id, ChatMessage.role == "user")
        .order_by(ChatMessage.created_at)
        .all()
    )

    msg_count = len(messages)
    if msg_count == 0:
        return {
            "message_count": 0,
            "avg_length": 0,
            "vague_ratio": 0,
            "specific_ratio": 0,
            "history": [],
        }

    total_length = sum(len(msg.content) for msg in messages)
    avg_length = total_length / msg_count

    specific_keywords = [
        "specific",
        "detailed",
        "compare",
        "analyze",
        "explain",
        "format",
        "based on",
        "code",
        "example",
    ]

    specific_count = 0
    history_stats = []

    for i, msg in enumerate(messages):
        content = msg.content.lower()
        is_specific = (
            (len(content) > 50)
            or ("?" in content)
            or any(kw in content for kw in specific_keywords)
        )
        if is_specific:
            specific_count += 1

        history_stats.append(
            {"index": i + 1, "length": len(msg.content), "is_specific": is_specific}
        )

    vague_count = msg_count - specific_count

    return {
        "message_count": msg_count,
        "avg_length": round(avg_length, 2),
        "vague_ratio": round(vague_count / msg_count, 2),
        "specific_ratio": round(specific_count / msg_count, 2),
        "history": history_stats,
    }


@router.post("/prompt-quality")
def check_prompt_quality(req: PromptRequest):
    content = req.message.strip().lower()

    if len(content) < 15:
        return {
            "tip": "Short & sweet. Try adding a bit more context if NYRA's answer is too general!"
        }

    specific_keywords = ["format", "list", "compare", "code", "example", "step-by-step"]
    has_format = any(kw in content for kw in specific_keywords)

    if has_format:
        return {
            "tip": "Nice! Specifying formats (like lists or code) helps NYRA give you exactly what you need."
        }

    if "?" not in content and len(content) > 100:
        return {
            "tip": "Great details! If you're looking for a specific answer, making sure to include a clear question helps."
        }

    return {
        "tip": "Solid prompt! The more context you provide, the better the insights."
    }
