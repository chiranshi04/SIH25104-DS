"""
schemas.py
----------
Yahan AI contract aur browser API ka data define hota hai.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class HistoryItem(BaseModel):
    user: str
    assistant: str


class AIRequest(BaseModel):
    conversation_id: str
    message: str
    history: List[HistoryItem] = Field(default_factory=list)


class Source(BaseModel):
    document: str
    page: Optional[int] = None
    section: Optional[str] = None


class AIResponse(BaseModel):
    answer: str
    language: str
    sources: List[Source] = Field(default_factory=list)
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="AI's confidence score between 0 and 1",
    )


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = Field(
        default=None,
        description="UUID for this conversation; omitted to start a new one",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User's question, in any language",
        examples=["Scholarship ki eligibility kya hai?"],
    )

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be empty or blank.")
        return value


class ChatResponse(AIResponse):
    conversation_id: str
    response_id: int


class ConversationMessage(BaseModel):
    id: int
    sender: str
    message: str
    timestamp: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    sources: List[Source] = Field(default_factory=list)
    response_id: Optional[int] = None


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: List[ConversationMessage]


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class ConversationListItem(BaseModel):
    id: str
    updated_at: str
    preview: str


class ConversationListResponse(BaseModel):
    conversations: List[ConversationListItem]
