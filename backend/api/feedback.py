"""Feedback endpoint for assistant responses."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user_optional
from backend.database.connection import get_db
from backend.database.feedback_schemas import FeedbackRequest, FeedbackResponse
from backend.database.models import Conversation, Feedback, Message, Response, User

router = APIRouter(tags=["Feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
def save_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> FeedbackResponse:
    response = db.scalar(
        select(Response)
        .where(Response.id == request.response_id)
        .join(Response.message)
        .join(Message.conversation)
    )
    if response is None:
        raise HTTPException(status_code=404, detail="Response not found")

    conversation = response.message.conversation
    if request.conversation_id is not None and request.conversation_id != conversation.id:
        raise HTTPException(status_code=400, detail="conversation_id does not match the response")
    if conversation.user_id is not None and (
        current_user is None or current_user.id != conversation.user_id
    ):
        raise HTTPException(status_code=403, detail="You cannot give feedback on this response")

    row = db.scalar(select(Feedback).where(Feedback.response_id == response.id))
    now = datetime.now(timezone.utc)
    if row is None:
        row = Feedback(response_id=response.id, feedback=request.feedback, created_at=now)
        db.add(row)
    else:
        row.feedback = request.feedback
        row.created_at = now
    db.commit()
    db.refresh(row)
    return FeedbackResponse(
        response_id=response.id,
        feedback=row.feedback,
        created_at=row.created_at,
    )
