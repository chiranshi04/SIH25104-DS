# Project context (read this before every task)

## What this is
Language-agnostic institutional chatbot. Users ask questions in English/Hindi/Hinglish/code-mixed text and see: answer, detected language, sources, confidence, conversation history, feedback. Admins/staff log in, manage documents, notices, feedback, users.
I (Student 2) own: FastAPI backend, API, Pydantic schemas, PostgreSQL, auth, conversations, frontend/GUI, admin dashboard, document upload API, feedback API, error handling, app security, tests, Docker, integration.
Student 1 owns: embeddings, ChromaDB, chunking, retrieval, RAG logic, LLM prompts. NEVER implement or touch these.

## Stable AI <-> Backend contract (do NOT change field names or shapes)
Backend -> AI:
{"conversation_id": "abc123", "message": "Scholarship ki eligibility kya hai?", "history": [{"user": "...", "assistant": "..."}]}
AI -> Backend:
{"answer": "...", "language": "hinglish", "sources": [{"document": "scholarship.pdf", "page": 3, "section": "Eligibility"}], "confidence": 0.91}
The backend->browser response may ADD fields (conversation_id, response_id) but must always contain answer, language, sources, confidence exactly as the AI returned them. The frontend must never invent or edit sources/language/confidence.

## Architecture
Browser -> FastAPI -> ai_service (single interface) -> Student 1 module (ChromaDB + LLM)
FastAPI -> PostgreSQL for application data. Documents: Admin -> FastAPI validates/stores -> Student 1 ingestion interface.

## Locked technical decisions
- Frontend: plain HTML/CSS/JS in frontend/, served by FastAPI at /app. No React.
- Backend layout: backend/{main.py, config.py, api/, database/{connection,models,schemas}.py, services/, auth/security.py, scripts/, tests/}. Never put logic in main.py beyond app wiring.
- SQLAlchemy 2.0 sync + psycopg2-binary; portable column types only (tests run on SQLite).
- Passwords: bcrypt package directly. JWT: PyJWT, HS256, 60 min expiry. Bearer token in Authorization header.
- Roles: public (no token, can chat), student, staff, admin. Registration always creates "student".
- Config only from .env via backend/config.py. Never hard-code secrets/credentials. Never commit .env. Keep .env.example up to date with every new variable.
- All IDs returned to the frontend are stable; conversation ids are UUID strings.

## Rules for every task
1. Read this file and inspect the existing code before changing anything. Keep existing working behavior unless the task says otherwise.
2. Keep code comments in the same simple Hinglish style as the existing files.
3. No fake data, no fabricated sources, no fake AI answers outside AI_MODE=dummy.
4. Do not build features from later phases.
5. Add every new dependency to requirements.txt with a pinned version.
6. Never print or paste secrets from .env in your report.
7. Actually run the app and the commands you claim work. In your final report include: files created/changed, exact commands you ran with their real output (trimmed), and anything that did NOT work or that you could not test. Do not claim success for anything you did not run.
