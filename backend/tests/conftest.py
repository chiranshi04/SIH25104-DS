"""Shared pytest fixtures for the backend API."""

from pathlib import Path
import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth.security import create_access_token, hash_password
from backend.config import settings
from backend.database.connection import Base, get_db
from backend.database.models import User
from backend.database.schemas import AIResponse
from backend.errors import AIInvalidResponseError, AITimeoutError, AIUnavailableError
from backend.main import app
from backend.security.rate_limit import limiter


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 10)
    monkeypatch.setattr(settings, "AI_MODE", "dummy")
    with limiter._lock:
        limiter._events.clear()
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()


class FakeAI:
    def __init__(self):
        self.mode = "normal"
        self.calls: list[dict] = []
        self.ingestion_mode = "success"

    def answer(self, message: str, conversation_id: str, history: list[dict]):
        self.calls.append(
            {
                "message": message,
                "conversation_id": conversation_id,
                "history": history,
            }
        )
        if self.mode == "unavailable":
            raise AIUnavailableError("fake AI unavailable")
        if self.mode == "timeout":
            raise AITimeoutError("fake AI timeout")
        if self.mode == "invalid":
            raise AIInvalidResponseError("fake AI invalid response")
        return AIResponse.model_validate({
            "answer": f"fake answer for {message}",
            "language": "hinglish",
            "sources": [{"document": "handbook.pdf", "page": 2, "section": "General"}],
            "confidence": 0.91,
        })

    def ingest_document(self, file_path: str, document_id: int, original_filename: str):
        if self.ingestion_mode == "failure":
            return {"status": "failed", "error": "fake ingestion failed"}
        return {"status": "ingested", "error": None}

    def delete_document(self, document_id: int, original_filename: str):
        return {"status": "deleted", "error": None}


@pytest.fixture()
def fake_ai(monkeypatch: pytest.MonkeyPatch):
    fake = FakeAI()
    import backend.api.chat as chat_api
    import backend.services.ai_service as ai_service
    import backend.services.ingestion_service as ingestion_service

    monkeypatch.setattr(chat_api, "get_ai_answer", fake.answer)
    monkeypatch.setattr(ai_service, "answer", fake.answer)
    monkeypatch.setattr(ingestion_service, "ingest_document", fake.ingest_document)
    monkeypatch.setattr(ingestion_service, "delete_document", fake.delete_document)
    return fake


def make_user(db: Session, name: str, email: str, role: str, active: bool = True) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=hash_password("CorrectHorseBatteryStaple1!"),
        role=role,
        is_active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def student_user(db_session: Session):
    return make_user(db_session, "Student", "student@example.com", "student")


@pytest.fixture()
def staff_user(db_session: Session):
    return make_user(db_session, "Staff", "staff@example.com", "staff")


@pytest.fixture()
def admin_user(db_session: Session):
    return make_user(db_session, "Admin", "admin@example.com", "admin")


@pytest.fixture()
def student_token(student_user: User):
    return create_access_token(student_user.id, student_user.role)


@pytest.fixture()
def staff_token(staff_user: User):
    return create_access_token(staff_user.id, staff_user.role)


@pytest.fixture()
def admin_token(admin_user: User):
    return create_access_token(admin_user.id, admin_user.role)


@pytest.fixture()
def auth_headers():
    return lambda token: {"Authorization": f"Bearer {token}"}
