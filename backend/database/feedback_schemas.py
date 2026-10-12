"""Schemas for answer feedback."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    response_id: int = Field(..., ge=1)
    feedback: Literal["positive", "negative"]
    conversation_id: str | None = None


class FeedbackResponse(BaseModel):
    response_id: int
    feedback: Literal["positive", "negative"]
    created_at: datetime
