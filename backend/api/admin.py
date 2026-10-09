"""Admin dashboard endpoints for users, feedback, and statistics."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.auth.dependencies import require_roles
from backend.database.admin_schemas import (
    AdminStats,
    AdminUserResponse,
    FeedbackPage,
    FeedbackRow,
    UserPatchRequest,
)
from backend.database.connection import get_db
from backend.database.models import Conversation, Feedback, Message, Notice, Response, User

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("staff", "admin")),
):
    return db.scalars(select(User).order_by(User.created_at.desc())).all()


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def patch_user(
    user_id: int,
    request: UserPatchRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and (
        (request.role is not None and request.role != "admin")
        or request.is_active is False
    ):
        raise HTTPException(status_code=400, detail="An admin cannot demote or deactivate themselves")
    if request.role is not None:
        user.role = request.role
    if request.is_active is not None:
        user.is_active = request.is_active
    db.commit()
    db.refresh(user)
    return user


@router.get("/feedback", response_model=FeedbackPage)
def list_feedback(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    feedback_value: str | None = Query(default=None, alias="feedback"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("staff", "admin")),
):
    query = select(Feedback).options(
        selectinload(Feedback.response)
        .selectinload(Response.message)
        .selectinload(Message.conversation)
        .selectinload(Conversation.messages),
        selectinload(Feedback.response).selectinload(Response.sources),
    )
    count_query = select(func.count(Feedback.id))
    if feedback_value in {"positive", "negative"}:
        query = query.where(Feedback.feedback == feedback_value)
        count_query = count_query.where(Feedback.feedback == feedback_value)
    total = db.scalar(count_query) or 0
    rows = db.scalars(
        query.order_by(Feedback.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = []
    for row in rows:
        response = row.response
        assistant_message = response.message
        question = ""
        if assistant_message and assistant_message.conversation:
            user_messages = [
                message
                for message in assistant_message.conversation.messages
                if message.sender == "user" and message.timestamp <= assistant_message.timestamp
            ]
            if user_messages:
                question = user_messages[-1].message
        items.append(
            FeedbackRow(
                feedback=row.feedback,
                created_at=row.created_at,
                question=question,
                answer=response.answer,
                language=response.language,
                confidence=response.confidence,
                sources=[
                    {
                        "document": source.document,
                        "page": source.page,
                        "section": source.section,
                    }
                    for source in response.sources
                ],
            )
        )
    return FeedbackPage(page=page, page_size=page_size, total=total, items=items)


@router.get("/stats", response_model=AdminStats)
def stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("staff", "admin")),
):
    return AdminStats(
        users=db.scalar(select(func.count(User.id))) or 0,
        conversations=db.scalar(select(func.count(Conversation.id))) or 0,
        notices=db.scalar(select(func.count(Notice.id))) or 0,
        feedback_positive=db.scalar(
            select(func.count(Feedback.id)).where(Feedback.feedback == "positive")
        )
        or 0,
        feedback_negative=db.scalar(
            select(func.count(Feedback.id)).where(Feedback.feedback == "negative")
        )
        or 0,
    )
