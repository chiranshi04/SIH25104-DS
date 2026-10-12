"""One stable boundary between the backend and Student 1's AI implementation."""

import importlib
import logging
from typing import Any

import httpx

from backend.config import settings
from backend.database.schemas import AIRequest, AIResponse
from backend.errors import (
    AIInvalidResponseError,
    AITimeoutError,
    AIUnavailableError,
)
from backend.services.dummy_ai_service import get_dummy_answer

logger = logging.getLogger(__name__)


_ALLOWED_MODES = {"dummy", "http", "module"}


def validate_ai_configuration() -> None:
    mode = settings.AI_MODE
    if mode not in _ALLOWED_MODES:
        raise RuntimeError("AI_MODE must be one of: dummy, http, module")
    if mode == "dummy" and settings.ENVIRONMENT.lower() == "production":
        raise RuntimeError("AI_MODE=dummy is not allowed when ENVIRONMENT=production")
    if mode == "http" and not settings.AI_BASE_URL:
        raise RuntimeError("AI_BASE_URL is required when AI_MODE=http")
    if mode == "module" and not settings.AI_MODULE_PATH:
        raise RuntimeError("AI_MODULE_PATH is required when AI_MODE=module")


def _module() -> Any:
    try:
        return importlib.import_module(settings.AI_MODULE_PATH)
    except ImportError as exc:
        raise AIUnavailableError("Could not load the configured AI module") from exc


def _validate_response(payload: Any) -> AIResponse:
    try:
        return AIResponse.model_validate(payload)
    except Exception as exc:
        raise AIInvalidResponseError("AI response did not match the required contract") from exc


def _http_answer(request: AIRequest) -> AIResponse:
    try:
        with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{settings.AI_BASE_URL}/answer",
                json=request.model_dump(),
            )
            if response.status_code < 200 or response.status_code >= 300:
                raise AIUnavailableError(f"AI HTTP endpoint returned status {response.status_code}")
            try:
                payload = response.json()
            except ValueError as exc:
                raise AIInvalidResponseError("AI response was not valid JSON") from exc
            return _validate_response(payload)
    except httpx.TimeoutException as exc:
        raise AITimeoutError("AI HTTP request timed out") from exc
    except AIInvalidResponseError:
        raise
    except AIUnavailableError:
        raise
    except httpx.RequestError as exc:
        raise AIUnavailableError("AI HTTP endpoint is unavailable") from exc


def _module_answer(request: AIRequest) -> AIResponse:
    try:
        answer = _module().answer(
            request.message,
            request.conversation_id,
            [item.model_dump() for item in request.history],
        )
    except TimeoutError as exc:
        raise AITimeoutError("AI module timed out") from exc
    except AIInvalidResponseError:
        raise
    except Exception as exc:
        raise AIUnavailableError("AI module is unavailable") from exc
    return _validate_response(answer)


def answer(message: str, conversation_id: str, history: list[dict]) -> AIResponse:
    """Return a validated AI response without exposing adapter details to routes."""
    validate_ai_configuration()
    request = AIRequest(conversation_id=conversation_id, message=message, history=history)
    if settings.AI_MODE == "dummy":
        return _validate_response(get_dummy_answer(request))
    if settings.AI_MODE == "http":
        return _http_answer(request)
    return _module_answer(request)


def _validate_operation_result(payload: Any, default_error: str) -> dict:
    if not isinstance(payload, dict):
        return {"status": "failed", "error": default_error}
    status = payload.get("status")
    if status not in {"pending", "ingested", "failed", "deleted"}:
        return {"status": "failed", "error": default_error}
    return {"status": status, "error": payload.get("error")}


def ingest_document(file_path: str, document_id: int, original_filename: str) -> dict:
    """Route document ingestion through the selected adapter."""
    validate_ai_configuration()
    if settings.AI_MODE == "dummy":
        return {"status": "pending", "error": "AI ingestion not connected yet"}
    if settings.AI_MODE == "module":
        try:
            result = _module().ingest_document(file_path, document_id, original_filename)
            return _validate_operation_result(result, "AI module returned an invalid ingestion result")
        except TimeoutError:
            return {"status": "failed", "error": "AI module ingestion timed out"}
        except Exception as exc:
            logger.exception("AI module ingestion failed: %s", exc)
            return {"status": "failed", "error": "AI module ingestion failed"}
    try:
        with open(file_path, "rb") as handle, httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{settings.AI_BASE_URL}/ingest",
                data={"document_id": str(document_id), "original_filename": original_filename},
                files={"file": (original_filename, handle)},
            )
            if response.status_code < 200 or response.status_code >= 300:
                return {"status": "failed", "error": f"AI ingestion returned status {response.status_code}"}
            return _validate_operation_result(response.json(), "AI ingestion returned an invalid result")
    except httpx.TimeoutException:
        return {"status": "failed", "error": "AI ingestion timed out"}
    except (httpx.RequestError, OSError, ValueError):
        return {"status": "failed", "error": "AI ingestion service is unavailable"}


def delete_document(document_id: int, original_filename: str) -> dict:
    """Route document deletion through the selected adapter."""
    validate_ai_configuration()
    if settings.AI_MODE == "dummy":
        return {"status": "pending", "error": "AI ingestion not connected yet"}
    if settings.AI_MODE == "module":
        try:
            result = _module().delete_document(document_id, original_filename)
            return _validate_operation_result(result, "AI module returned an invalid delete result")
        except Exception as exc:
            logger.exception("AI module deletion failed: %s", exc)
            return {"status": "failed", "error": "AI module deletion failed"}
    try:
        with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            response = client.delete(f"{settings.AI_BASE_URL}/documents/{document_id}")
            if response.status_code < 200 or response.status_code >= 300:
                return {"status": "failed", "error": f"AI deletion returned status {response.status_code}"}
            if not response.content:
                return {"status": "deleted", "error": None}
            return _validate_operation_result(response.json(), "AI deletion returned an invalid result")
    except httpx.TimeoutException:
        return {"status": "failed", "error": "AI deletion timed out"}
    except (httpx.RequestError, ValueError):
        return {"status": "failed", "error": "AI deletion service is unavailable"}


def health() -> dict:
    """Cheap adapter health probe that never raises to the API route."""
    try:
        validate_ai_configuration()
        if settings.AI_MODE == "dummy":
            return {"status": "ok", "mode": "dummy"}
        if settings.AI_MODE == "module":
            target = _module()
            probe = getattr(target, "health", None)
            return {"status": "ok", "mode": "module", "detail": probe() if callable(probe) else "module loaded"}
        with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            response = client.get(settings.AI_BASE_URL)
            if response.status_code >= 500:
                return {"status": "unavailable", "mode": "http"}
        return {"status": "ok", "mode": "http"}
    except Exception as exc:
        logger.warning("AI health check failed: %s", exc)
        return {"status": "unavailable", "detail": "AI service unavailable"}
