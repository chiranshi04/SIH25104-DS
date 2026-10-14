# Phase 15 — Security Hardening Checklist

**Project:** SIH25104 Language-Agnostic Institutional Chatbot  
**Phase:** 15  
**Date:** 2026-10-14  
**Commit:** to be recorded after push

## Configuration and secrets

- [x] `.env` is ignored by Git; `.env.example` contains placeholders only.
- [x] `uploads/` is ignored by Git and is outside the frontend directory.
- [x] Production startup rejects the development/default `SECRET_KEY` and keys shorter than 32 characters.
- [x] Production startup rejects `AI_MODE=dummy`; supported production modes remain `http` and `module`.
- [x] Production startup rejects wildcard CORS.
- [x] AI configuration is validated during FastAPI lifespan startup.
- [x] API documentation can be disabled in production with `DOCS_ENABLED=false`.

## Authentication and authorization

- [x] JWT decoding pins the algorithm to HS256 and validates expiration through PyJWT.
- [x] Every authenticated request reloads the user from the database; role and `is_active` are not trusted from the token.
- [x] A malformed, expired, or unknown-user token returns generic `401 Invalid authentication credentials`.
- [x] A valid token for a deactivated user returns `403 User account is inactive`.
- [x] Login for inactive accounts remains a generic `401` to avoid account-state disclosure.
- [x] Admin/staff route authorization uses database-revalidated roles.
- [x] Password hashes are not included in user API responses.

## CORS, browser headers, and frontend policy

- [x] CORS uses the comma-separated `CORS_ORIGINS` environment setting; no wildcard default.
- [x] CORS methods and headers are explicitly allow-listed.
- [x] Responses include `X-Content-Type-Options: nosniff`.
- [x] Responses include `X-Frame-Options: DENY`.
- [x] Responses include a restrictive Content Security Policy with same-origin scripts/styles and no objects.
- [x] Responses include `Referrer-Policy: no-referrer` and a restrictive `Permissions-Policy`.
- [x] Frontend dynamic output uses `textContent`; no `innerHTML` sinks are present.
- [x] Frontend pages use external local JavaScript files; no inline event handlers/scripts/styles are required.

## Rate limiting and request sizes

- [x] Registration: 5 requests per IP per 60 seconds.
- [x] Login: 10 requests per IP per 60 seconds.
- [x] Guest chat: 30 requests per IP per 60 seconds.
- [x] Authenticated chat: 60 requests per user per 60 seconds.
- [x] Admin document upload: 10 requests per user per 60 seconds.
- [x] Rate-limit responses return HTTP 429 with `Retry-After`.
- [x] `/chat` rejects a declared body larger than `MAX_CHAT_BODY_BYTES` (default 10 KiB).
- [x] Upload streaming enforces the configured `MAX_UPLOAD_MB` limit without loading the full file into memory.

## Verification commands

Run from the repository root:

```bash
python -m compileall -q backend
pytest -q
pip-audit -r requirements.txt
```

The repository currently contains no pytest test functions, so `pytest -q` is a collection smoke check rather than a behavioral suite. The application smoke checks below cover the Phase 15 controls.

```bash
python - <<'PY'
from fastapi.testclient import TestClient
from backend.main import app

with TestClient(app) as client:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['x-frame-options'] == 'DENY'
    assert "script-src 'self'" in response.headers['content-security-policy']

    allowed = client.options('/health', headers={
        'Origin': 'http://localhost:8000',
        'Access-Control-Request-Method': 'GET',
    })
    assert allowed.status_code == 200
    assert allowed.headers['access-control-allow-origin'] == 'http://localhost:8000'

    blocked = client.options('/health', headers={
        'Origin': 'https://evil.example',
        'Access-Control-Request-Method': 'GET',
    })
    assert blocked.status_code == 400

    oversized = client.post('/chat', headers={'Content-Length': '20000'}, content='{}')
    assert oversized.status_code == 413

print('Phase 15 smoke checks passed')
PY
```

## Dependency scan result

`pip-audit -r requirements.txt` completed with **No known vulnerabilities found** after updating the vulnerable direct pins for FastAPI/Starlette, `python-dotenv`, PyJWT, and `python-multipart`.

## Operational notes

- The limiter is intentionally process-local and in-memory. For multiple workers or multiple instances, replace it with a shared store (for example Redis) before horizontal scaling.
- Rate limiting is keyed by the socket peer address. If a trusted reverse proxy is introduced, configure proxy handling deliberately; do not blindly trust arbitrary `X-Forwarded-For` headers.
- Set `CORS_ORIGINS` to the exact deployed frontend origins, set `DOCS_ENABLED=false` unless documentation is needed, and use a random production `SECRET_KEY`.
