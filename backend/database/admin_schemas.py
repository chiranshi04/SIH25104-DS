"""Phase 9 admin and notice API schemas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class NoticeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=10000)
    is_active: bool = True


class NoticeUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1, max_length=10000)
    is_active: Optional[bool] = None


class NoticeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    is_active: bool
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime


class AdminUserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


class UserPatchRequest(BaseModel):
    role: Optional[Literal["student", "staff", "admin"]] = None
    is_active: Optional[bool] = None


class FeedbackRow(BaseModel):
    feedback: Literal["positive", "negative"]
    created_at: datetime
    question: str
    answer: str
    language: str
    confidence: float
    sources: list[dict]


class FeedbackPage(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[FeedbackRow]


class AdminStats(BaseModel):
    users: int
    conversations: int
    notices: int
    feedback_positive: int
    feedback_negative: int
