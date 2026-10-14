import sys
from types import SimpleNamespace

import httpx
import pytest

from backend.database.schemas import AIResponse
from backend.errors import AIInvalidResponseError, AITimeoutError, AIUnavailableError
from backend.services import ai_service


def request():
    return ai_service.AIRequest(conversation_id="c", message="hello", history=[])


class Response:
    def __init__(self, status_code=200, payload=None, content=b"x"):
        self.status_code = status_code
        self._payload = payload
        self.content = content

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class Client:
    def __init__(self, response=None, error=None, calls=None):
        self.response = response
        self.error = error
        self.calls = calls if calls is not None else []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def post(self, *args, **kwargs):
        self.calls.append(("post", args, kwargs))
        if self.error:
            raise self.error
        return self.response

    def delete(self, *args, **kwargs):
        self.calls.append(("delete", args, kwargs))
        if self.error:
            raise self.error
        return self.response

    def get(self, *args, **kwargs):
        self.calls.append(("get", args, kwargs))
        if self.error:
            raise self.error
        return self.response


def test_dummy_and_configuration_validation(monkeypatch):
    monkeypatch.setattr(ai_service.settings, "AI_MODE", "dummy")
    monkeypatch.setattr(ai_service, "get_dummy_answer", lambda _: {"answer": "a", "language": "en", "sources": [], "confidence": 0.5})
    assert ai_service.answer("hello", "c", []).answer == "a"
    monkeypatch.setattr(ai_service.settings, "AI_MODE", "invalid")
    with pytest.raises(RuntimeError):
        ai_service.validate_ai_configuration()
    monkeypatch.setattr(ai_service.settings, "AI_MODE", "http")
    monkeypatch.setattr(ai_service.settings, "AI_BASE_URL", "")
    with pytest.raises(RuntimeError):
        ai_service.validate_ai_configuration()
    monkeypatch.setattr(ai_service.settings, "AI_MODE", "module")
    monkeypatch.setattr(ai_service.settings, "AI_MODULE_PATH", "")
    with pytest.raises(RuntimeError):
        ai_service.validate_ai_configuration()


def test_module_adapter_success_timeout_and_invalid(monkeypatch):
    module = SimpleNamespace(answer=lambda *args: {"answer": "module", "language": "en", "sources": [], "confidence": 0.8})
    monkeypatch.setitem(sys.modules, "fake_module", module)
    monkeypatch.setattr(ai_service.settings, "AI_MODE", "module")
    monkeypatch.setattr(ai_service.settings, "AI_MODULE_PATH", "fake_module")
    assert ai_service.answer("hello", "c", []).answer == "module"
    monkeypatch.setattr(module, "answer", lambda *args: (_ for _ in ()).throw(TimeoutError()))
    with pytest.raises(AITimeoutError):
        ai_service.answer("hello", "c", [])
    monkeypatch.setattr(module, "answer", lambda *args: {"invalid": True})
    with pytest.raises(AIInvalidResponseError):
        ai_service.answer("hello", "c", [])
    monkeypatch.setattr(ai_service.settings, "AI_MODULE_PATH", "missing_module")
    with pytest.raises(AIUnavailableError):
        ai_service.answer("hello", "c", [])


def test_http_answer_success_and_failures(monkeypatch):
    valid = {"answer": "http", "language": "en", "sources": [], "confidence": 0.7}
    monkeypatch.setattr(ai_service.settings, "AI_MODE", "http")
    monkeypatch.setattr(ai_service.settings, "AI_BASE_URL", "http://ai")
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **_: Client(Response(payload=valid)))
    assert ai_service.answer("hello", "c", []).answer == "http"
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **_: Client(Response(status_code=503, payload={})))
    with pytest.raises(AIUnavailableError):
        ai_service.answer("hello", "c", [])
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **_: Client(Response(payload=ValueError())))
    with pytest.raises(AIInvalidResponseError):
        ai_service.answer("hello", "c", [])
    timeout = httpx.ReadTimeout("timeout", request=httpx.Request("POST", "http://ai"))
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **_: Client(error=timeout))
    with pytest.raises(AITimeoutError):
        ai_service.answer("hello", "c", [])
    error = httpx.ConnectError("down", request=httpx.Request("POST", "http://ai"))
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **_: Client(error=error))
    with pytest.raises(AIUnavailableError):
        ai_service.answer("hello", "c", [])


def test_module_and_http_document_operations(monkeypatch, tmp_path):
    module = SimpleNamespace(
        ingest_document=lambda *args: {"status": "ingested", "error": None},
        delete_document=lambda *args: {"status": "deleted", "error": None},
    )
    monkeypatch.setitem(sys.modules, "ops_module", module)
    monkeypatch.setattr(ai_service.settings, "AI_MODE", "module")
    monkeypatch.setattr(ai_service.settings, "AI_MODULE_PATH", "ops_module")
    assert ai_service.ingest_document(str(tmp_path / "x"), 1, "x")["status"] == "ingested"
    assert ai_service.delete_document(1, "x")["status"] == "deleted"
    monkeypatch.setattr(module, "ingest_document", lambda *args: {"bad": True})
    assert ai_service.ingest_document(str(tmp_path / "x"), 1, "x")["status"] == "failed"
    monkeypatch.setattr(ai_service.settings, "AI_MODE", "http")
    monkeypatch.setattr(ai_service.settings, "AI_BASE_URL", "http://ai")
    path = tmp_path / "x.txt"
    path.write_text("x")
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **_: Client(Response(payload={"status": "ingested", "error": None})))
    assert ai_service.ingest_document(str(path), 1, "x.txt")["status"] == "ingested"
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **_: Client(Response(status_code=500, payload={})))
    assert ai_service.delete_document(1, "x")["status"] == "failed"
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **_: Client(Response(status_code=500, payload={})))
    assert ai_service.ingest_document(str(path), 1, "x.txt")["status"] == "failed"


def test_health_modes(monkeypatch):
    monkeypatch.setattr(ai_service.settings, "AI_MODE", "dummy")
    assert ai_service.health()["status"] == "ok"
    module = SimpleNamespace(health=lambda: "healthy")
    monkeypatch.setitem(sys.modules, "health_module", module)
    monkeypatch.setattr(ai_service.settings, "AI_MODE", "module")
    monkeypatch.setattr(ai_service.settings, "AI_MODULE_PATH", "health_module")
    assert ai_service.health()["detail"] == "healthy"
    monkeypatch.setattr(ai_service.settings, "AI_MODE", "http")
    monkeypatch.setattr(ai_service.settings, "AI_BASE_URL", "http://ai")
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **_: Client(Response(status_code=200)))
    assert ai_service.health()["status"] == "ok"
    monkeypatch.setattr(ai_service.httpx, "Client", lambda **_: Client(error=Exception("down")))
    assert ai_service.health()["status"] == "unavailable"
