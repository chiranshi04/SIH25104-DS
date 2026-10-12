"""
conversations.py
----------------
Conversation restore aur listing endpoints yahan define hote hain.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.auth.dependencies import get_current_user, get_current_user_optional
from backend.database.connection import get_db
from backend.database.models import Conversation, Message, User
from backend.database.schemas import (
    ConversationHistoryResponse,
    ConversationListItem,
    ConversationListResponse,
    ConversationMessage,
    Source,
)
from backend.services.conversation_service import get_conversation_messages

router = APIRouter(tags=["Conversations"])


def _check_conversation_access(
    conversation: Conversation, current_user: User | None
) -> None:
    if conversation.user_id is not None and (
        current_user is None or conversation.user_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="You cannot access this conversation")


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationListResponse:
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.updated_at.desc())
    ).all()

    items = []
    for conversation in rows:
        preview = next(
            (
                message.message
                for message in conversation.messages
                if message.sender == "user"
            ),
            "",
        )
        items.append(
            ConversationListItem(
                id=conversation.id,
                updated_at=conversation.updated_at.isoformat(),
                preview=preview[:60],
            )
        )
    return ConversationListResponse(conversations=items)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    # TODO Phase 8: ownership/auth policy ko future roles ke saath expand karna hai.
    conversation = get_conversation_messages(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    _check_conversation_access(conversation, current_user)

    messages = []
    for message in conversation.messages:
        response = message.response
        messages.append(
            ConversationMessage(
                id=message.id,
                sender=message.sender,
                message=message.message,
                timestamp=message.timestamp.isoformat(),
                language=response.language if response else None,
                confidence=response.confidence if response else None,
                sources=[
                    Source(
                        document=source.document,
                        page=source.page,
                        section=source.section,
                    )
                    for source in response.sources
                ]
                if response
                else [],
                response_id=response.id if response else None,
                feedback=response.feedback.feedback if response and response.feedback else None,
            )
        )

    return ConversationHistoryResponse(
        conversation_id=conversation.id,
        messages=messages,
    )
