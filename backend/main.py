"""FastAPI application wiring and centralized error handling."""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.api import admin, auth, chat, conversations, documents, feedback, notices
from backend.config import settings
from backend.database.connection import get_db, init_db
from backend.errors import AppError, ErrorCode
from backend.services.ai_service import health as ai_health
from backend.services.ai_service import validate_ai_configuration

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App start par database tables ensure karo."""
    validate_ai_configuration()
    if settings.AI_MODE == "dummy":
        logger.warning(
            "AI_MODE=dummy is active: this is development/test only and is not a real AI service."
        )
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Language-Agnostic Institutional Chatbot backend (SIH25104)",
    lifespan=lifespan,
)


def error_response(detail: str, code: str, status_code: int, request_id: str | None = None):
    response = JSONResponse(
        status_code=status_code,
        content={"detail": detail, "code": code},
    )
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    friendly = {
        ErrorCode.AI_UNAVAILABLE: "Sorry, the AI service is temporarily unavailable. Please try again.",
        ErrorCode.AI_TIMEOUT: "The AI service took too long to respond. Please try again.",
        ErrorCode.AI_INVALID_RESPONSE: "The AI service returned an invalid response.",
        ErrorCode.DB_UNAVAILABLE: "Database is temporarily unavailable. Please try again.",
        ErrorCode.UPLOAD_FAILED: "Upload failed. Please try again.",
    }
    return error_response(friendly.get(exc.code, exc.detail), exc.code, exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    detail = "Invalid request. Please check your input."
    for error in exc.errors():
        location = error.get("loc", ())
        message = error.get("msg", "")
        if "message" in location and ("at most 1000" in message or "too_long" in str(error)):
            detail = "Message is too long (max 1000 characters)"
            break
        if "message" in location and ("empty" in message.lower() or "blank" in message.lower()):
            detail = "Message cannot be empty"
            break
        if error.get("type") == "json_invalid":
            detail = "Request body must be valid JSON."
    return error_response(detail, ErrorCode.VALIDATION_ERROR, 422)


@app.exception_handler(OperationalError)
@app.exception_handler(DBAPIError)
async def database_error_handler(request: Request, exc: Exception):
    logger.warning("Database unavailable for %s %s", request.method, request.url.path)
    return error_response(
        "Database is temporarily unavailable. Please try again.",
        ErrorCode.DB_UNAVAILABLE,
        503,
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    code_by_status = {
        400: ErrorCode.VALIDATION_ERROR,
        422: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        413: ErrorCode.UPLOAD_FAILED,
    }
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
    if exc.status_code == 401:
        detail = "Invalid authentication credentials"
    return error_response(
        detail,
        code_by_status.get(exc.status_code, ErrorCode.INTERNAL_ERROR),
        exc.status_code,
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    request_id = str(uuid4())
    logger.exception("Unhandled exception request_id=%s", request_id)
    return error_response(
        "Something went wrong on our side.",
        ErrorCode.INTERNAL_ERROR,
        500,
        request_id,
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")

app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(auth.router)
app.include_router(notices.router)
app.include_router(admin.router)
app.include_router(documents.router)
app.include_router(feedback.router)


@app.get("/")
def root():
    return {"message": "SIH25104 Chatbot backend is running.", "docs": "/docs"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/ai")
def ai_health_check():
    return ai_health()


@app.get("/health/db")
def database_health_check(db: Session = Depends(get_db)):
    """Database connection ko simple SELECT 1 se check karo."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
