"""
chat.py
-------
Yeh file /chat API route define karti hai.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user_optional
from backend.database.connection import get_db
from backend.database.models import Conversation, User
from backend.database.schemas import AIRequest, AIResponse, ChatRequest, ChatResponse
from backend.services.conversation_service import (
    build_history,
    get_or_create_conversation,
    save_turn,
)
from backend.services.ai_service import answer as get_ai_answer

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> ChatResponse:
    """Message process karke successful turn ko database mein save karo."""
    existing_conversation = (
        db.get(Conversation, request.conversation_id)
        if request.conversation_id
        else None
    )
    if existing_conversation is not None and current_user is not None:
        if existing_conversation.user_id is None:
            raise HTTPException(
                status_code=403,
                detail="Authenticated users cannot take over anonymous conversations",
            )
        if existing_conversation.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You cannot access this conversation")

    conversation = get_or_create_conversation(
        db,
        request.conversation_id,
        current_user.id if current_user else None,
    )
    if conversation.user_id is not None and (
        current_user is None or conversation.user_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="You cannot access this conversation")

    history = build_history(db, conversation.id)
    ai_request = AIRequest(
        conversation_id=conversation.id,
        message=request.message,
        history=history,
    )

    logger.info(
        "AIRequest sent: conversation_id=%s history_count=%d message_length=%d",
        ai_request.conversation_id,
        len(ai_request.history),
        len(ai_request.message),
    )
    ai_response: AIResponse = get_ai_answer(
        ai_request.message,
        ai_request.conversation_id,
        [item.model_dump() for item in ai_request.history],
    )
    response_id = save_turn(db, conversation.id, request.message, ai_response)

    return ChatResponse(
        **ai_response.model_dump(),
        conversation_id=conversation.id,
        response_id=response_id,
    )
