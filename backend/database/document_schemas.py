"""Phase 10 document API schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    original_filename: str
    size_bytes: int
    uploaded_at: datetime
    uploaded_by_name: Optional[str]
    ingestion_status: str
    ingestion_error: Optional[str]


class DocumentDeleteResponse(BaseModel):
    deleted: bool
    warning: Optional[str] = None
