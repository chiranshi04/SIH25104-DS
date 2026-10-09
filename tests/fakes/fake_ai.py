"""Pytest-only fake AI adapter; production code must never import this module."""


def answer(message: str, conversation_id: str, history: list[dict]) -> dict:
    return {
        "answer": f"fake answer for {message}",
        "language": "hinglish",
        "sources": [],
        "confidence": 0.5,
    }


def ingest_document(file_path: str, document_id: int, original_filename: str) -> dict:
    return {"status": "ingested", "error": None}


def delete_document(document_id: int, original_filename: str) -> dict:
    return {"status": "deleted", "error": None}
