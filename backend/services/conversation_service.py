"""
conversation_service.py
-----------------------
Conversation aur message persistence ka business logic yahan hai.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.database.models import Conversation, Message, Response, Source
from backend.database.schemas import AIResponse


def get_or_create_conversation(
    db: Session, conversation_id: str | None, user_id: int | None = None
) -> Conversation:
    """Existing conversation reuse karo, warna valid UUID ke saath naya banao."""
    if conversation_id:
        try:
            UUID(conversation_id)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="conversation_id must be a valid UUID string.",
            )

        conversation = db.get(Conversation, conversation_id)
        if conversation:
            return conversation
    else:
        conversation_id = str(uuid4())

    conversation = Conversation(id=conversation_id, user_id=user_id)
    db.add(conversation)
    db.flush()
    return conversation


def build_history(
    db: Session, conversation_id: str, max_turns: int = 6
) -> list[dict[str, str]]:
    """Stored user aur assistant messages se chronological history banao."""
    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp, Message.id)
    ).all()

    turns: list[dict[str, str]] = []
    current_user: str | None = None
    for message in messages:
        if message.sender == "user":
            current_user = message.message
        elif message.sender == "assistant" and current_user is not None:
            turns.append({"user": current_user, "assistant": message.message})
            current_user = None

    return turns[-max_turns:]


def save_turn(
    db: Session,
    conversation_id: str,
    user_message: str,
    ai_response: AIResponse,
) -> int:
    """Ek transaction mein user, assistant, response aur sources save karo."""
    try:
        user_row = Message(
            conversation_id=conversation_id,
            sender="user",
            message=user_message,
        )
        db.add(user_row)
        db.flush()

        assistant_row = Message(
            conversation_id=conversation_id,
            sender="assistant",
            message=ai_response.answer,
        )
        db.add(assistant_row)
        db.flush()

        response_row = Response(
            message_id=assistant_row.id,
            answer=ai_response.answer,
            language=ai_response.language,
            confidence=ai_response.confidence,
        )
        db.add(response_row)
        db.flush()

        for source in ai_response.sources:
            db.add(
                Source(
                    response_id=response_row.id,
                    document=source.document,
                    page=source.page,
                    section=source.section,
                )
            )

        conversation = db.get(Conversation, conversation_id)
        if conversation is None:
            raise RuntimeError("Conversation disappeared before turn could be saved.")
        conversation.updated_at = datetime.now(timezone.utc)
        db.commit()
        return response_row.id
    except Exception:
        db.rollback()
        raise


def get_conversation_messages(db: Session, conversation_id: str) -> Conversation | None:
    """Conversation ko ordered messages aur response details ke saath load karo."""
    return db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            selectinload(Conversation.messages)
            .selectinload(Message.response)
            .selectinload(Response.sources)
        )
    )
