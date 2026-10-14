# SIH25104 Language-Agnostic Institutional Chatbot

A FastAPI backend and plain HTML/CSS/JavaScript frontend for an institutional chatbot. Users can ask questions in English, Hindi, Hinglish, or code-mixed text and receive the answer plus only the AI-returned language, sources, and confidence metadata.

Student 1's retrieval/LLM implementation remains behind the single adapter boundary in `backend/services/ai_service.py`. The default `AI_MODE=dummy` is for development only.

## Docker quick start

Requirements: Docker Engine with the Compose plugin.

1. Create the local environment file:

   ```bash
   cp .env.example .env
   ```

2. Replace the database password, `SECRET_KEY`, and admin placeholders in `.env`. For a production-like run, also set `ENVIRONMENT=production`, `DOCS_ENABLED=false` if desired, exact `CORS_ORIGINS`, and `AI_MODE=http` or `AI_MODE=module`.

3. Build and start PostgreSQL plus the backend:

   ```bash
   docker compose up --build
   ```

   The backend waits for the PostgreSQL healthcheck before starting. The database port is not published by default; the backend reaches PostgreSQL through the Compose service name `db`.

4. Open:

   - Frontend: <http://localhost:8000/app/>
   - API docs: <http://localhost:8000/docs> when `DOCS_ENABLED=true`
   - API health: <http://localhost:8000/health>
   - Database health: <http://localhost:8000/health/db>

5. Seed an administrator explicitly. The command does not run automatically and never uses a built-in default password:

   ```bash
   docker compose exec backend python -m backend.scripts.create_admin
   ```

6. Stop the stack without deleting named volumes:

   ```bash
   docker compose down
   ```

   For a destructive clean-database test, use `docker compose down -v`.

### Optional local PostgreSQL port

The database is intentionally private to the Compose network. To expose it for local tools, copy the example override and start Compose again:

```bash
cp docker-compose.override.example.yml docker-compose.override.yml
docker compose up --build
```

`docker-compose.override.yml` is ignored by Git.

### Student 1 AI service placeholder

The `ai` service block in `docker-compose.yml` is commented out. When Student 1 provides an image and confirms the interface, uncomment/configure that block and set:

```env
AI_MODE=http
AI_BASE_URL=http://ai:8001
```

No ChromaDB or retrieval container is implemented in this repository.

## Non-Docker quick start

Requirements: Python 3.12 and PostgreSQL 16 (or a compatible PostgreSQL installation).

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env with the local PostgreSQL URL and local secrets.
uvicorn backend.main:app --reload
```

The application is available at <http://127.0.0.1:8000/app/>. The PostgreSQL database must exist before startup; the application creates its ORM tables during the FastAPI lifespan.

## Environment variables

All runtime configuration is loaded from `.env` through `backend/config.py`. Never commit `.env`.

| Variable | Purpose | Example/placeholder |
|---|---|---|
| `ENVIRONMENT` | Development or production startup policy | `development` |
| `LOG_LEVEL` | Python logging level | `INFO` |
| `CORS_ORIGINS` | Exact comma-separated allowed browser origins | `http://localhost:8000` |
| `DOCS_ENABLED` | Enable `/docs`, `/redoc`, and OpenAPI | `true` |
| `MAX_CHAT_BODY_BYTES` | Declared `/chat` request body limit | `10240` |
| `DATABASE_URL` | SQLAlchemy PostgreSQL URL; Compose overrides it to use `db` | `postgresql://chatbot:password@localhost:5432/chatbot_db` |
| `POSTGRES_USER` | PostgreSQL container user | `chatbot` |
| `POSTGRES_PASSWORD` | PostgreSQL container password | replace placeholder |
| `POSTGRES_DB` | PostgreSQL container database | `chatbot_db` |
| `SECRET_KEY` | JWT signing key; at least 32 random characters in production | replace placeholder |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime | `60` |
| `UPLOAD_DIR` | Validated document storage directory | `./uploads` or `/app/uploads` |
| `MAX_UPLOAD_MB` | Maximum upload size | `10` |
| `AI_MODE` | `dummy`, `http`, or `module` adapter | `dummy` |
| `AI_BASE_URL` | Student 1 HTTP adapter base URL | empty or `http://ai:8001` |
| `AI_TIMEOUT_SECONDS` | AI request timeout | `30` |
| `AI_MODULE_PATH` | Dotted Student 1 module path | empty or `student1_ai.adapter` |
| `ADMIN_NAME` | Explicit admin seed name | `Admin User` |
| `ADMIN_EMAIL` | Explicit admin seed email | `admin@example.com` |
| `ADMIN_PASSWORD` | Explicit admin seed password | replace placeholder |

## Running tests

Install the pinned development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run the full suite and coverage report:

```bash
pytest -v --cov=backend --cov-report=term-missing
```

The tests use a fresh SQLite database and temporary upload directory. They do not require PostgreSQL, Docker, the real AI module, or network access.

## Project structure

```text
.
├── backend/
│   ├── main.py                 # FastAPI app wiring, middleware, error handlers
│   ├── config.py               # .env-backed settings
│   ├── api/                    # Auth, chat, conversations, documents, feedback, admin, notices
│   ├── auth/                   # bcrypt password and JWT helpers/dependencies
│   ├── database/               # SQLAlchemy models, connection, and Pydantic schemas
│   ├── services/               # AI boundary, conversation persistence, document validation
│   ├── security/               # Process-local rate limiting
│   ├── scripts/                # Explicit admin seeding command
│   └── tests/                  # SQLite-isolated pytest suite
├── frontend/                   # Plain HTML/CSS/JS served at /app
├── docs/                       # AI adapter integration notes
├── Dockerfile                  # Non-root Python 3.12 backend image
├── docker-compose.yml          # PostgreSQL + backend stack
├── requirements.txt            # Runtime dependencies only
├── requirements-dev.txt        # Pinned test dependencies
└── PROJECT_CONTEXT.md          # Project rules and stable AI contract
```

## Security notes

- Do not auto-create an administrator or commit credentials.
- Do not publish PostgreSQL's port unless local tooling explicitly requires it.
- Use `docker compose down -v` only when intentionally deleting the local database volume.
- For the full hardening verification list, see `SECURITY_CHECKLIST.md`.
