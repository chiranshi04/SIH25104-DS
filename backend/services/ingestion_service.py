"""Compatibility boundary for document ingestion; adapter logic lives in ai_service."""

from backend.services.ai_service import delete_document as _delete_document
from backend.services.ai_service import ingest_document as _ingest_document


def ingest_document(file_path: str, document_id: int, original_filename: str) -> dict:
    return _ingest_document(file_path, document_id, original_filename)


def delete_document(document_id: int, original_filename: str) -> dict:
    return _delete_document(document_id, original_filename)
