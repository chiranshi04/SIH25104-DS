# SIH25104 Chatbot — 5–7 Minute Demo Script

## Before the demo

Use the non-Docker local run in this sandbox, because Docker is unavailable here:

```bash
cp .env.example .env
# Configure PostgreSQL and local credentials in .env.
uvicorn backend.main:app --reload
```

For a real presentation, seed the administrator explicitly:

```bash
python -m backend.scripts.create_admin
```

Open <http://127.0.0.1:8000/app/>. Keep the login page and admin dashboard URLs ready in separate tabs.

## 0:00–0:45 — Introduce the project

**Say:**

> This is a language-agnostic institutional chatbot. The browser talks only to the FastAPI backend. The backend owns authentication, conversations, feedback, document validation, and the admin area. AI integration is isolated behind one stable adapter contract, so Student 1's retrieval and LLM implementation can plug in without changing the browser API.

Point to the chat interface and mention that each response can contain the answer, detected language, sources, and confidence returned by the backend.

## 0:45–2:00 — Chat in three language styles

Submit these questions one at a time:

1. **English:** `How do I apply for a scholarship?`
2. **Hindi:** `छात्रवृत्ति के लिए आवेदन कैसे करें?`
3. **Hinglish:** `Scholarship ke liye eligibility kya hai?`
4. **Code-mixed:** `What documents chahiye for hostel admission?`

**Say:**

> The frontend displays metadata returned by the backend. It does not fabricate or infer language, confidence, or sources. The same rendering path is used for live answers and restored conversation history.

If the local environment is using `AI_MODE=dummy`, say explicitly:

> This visible response is the development dummy adapter. It confirms the API contract and UI flow, not Student 1's semantic language detection or retrieval quality.

## 2:00–2:45 — Conversation continuity and restore

Ask a first question:

```text
What is the application deadline?
```

Then ask in the same conversation:

```text
And what is the required format?
```

Refresh the page, open the conversation history, and select the conversation.

**Say:**

> The second request carries the conversation identifier. The backend reconstructs the prior turns before calling the AI adapter. After refresh, the conversation list and detail endpoint restore the saved messages and their metadata.

## 2:45–3:45 — Authentication and admin area

Open the login page and log in with the seeded admin account. Open the admin dashboard.

Show:

- Overview statistics
- Notices
- Feedback
- Users
- Documents

Create a short notice such as:

```text
Title: Scholarship help desk
Content: Visit the student office for application support.
```

Return to the public chat page and show that the active notice is visible. Optionally edit and delete it.

**Say:**

> The frontend access guard is only a user-experience feature. The actual permission enforcement is on the backend. Staff can manage notices and view reports, while only admins can change user roles, active states, or documents.

## 3:45–4:45 — Document validation and ingestion boundary

As admin, open Documents and upload a small valid `.txt` or `.pdf` file. Show the returned filename, size, and ingestion status.

Then demonstrate one rejected file, such as an `.exe`, and show the visible error message.

**Say:**

> The backend validates extension, MIME type, magic bytes, size, duplicate content, and safe storage names before calling the AI ingestion boundary. In dummy mode, ingestion remains pending because no real Student 1 ingestion service is connected. We do not claim document-grounded answers in that mode.

When Student 1's service is available, repeat this flow with `AI_MODE=http` and confirm that ingestion and document-grounded answering come from the real service.

## 4:45–5:30 — Feedback and admin reporting

Return to a response and submit positive feedback. Submit negative feedback on another response. Open Admin → Feedback and show both values.

**Say:**

> Feedback is persisted against the response and is visible to authorized staff and admins. The report includes the question, answer, language, confidence, and sources returned by the backend.

## 5:30–6:30 — Error handling and security

Show or explain these verified behaviors:

- Student token requesting an admin endpoint returns **403**.
- Guest chat remains available.
- Invalid upload returns **400**.
- Oversized chat request returns **413**.
- Security headers include `nosniff` and `DENY` framing.
- CORS allows configured origins and blocks an unconfigured origin.
- JWT requests revalidate the user and role from the database.

**Say:**

> Errors use standardized response codes and human-readable details. Rate limits protect registration, login, chat, and uploads. Production startup rejects a weak secret, wildcard CORS, and dummy AI mode.

## 6:30–7:00 — Close with verification status

**Say:**

> The automated suite has 42 passing tests and 92 percent total backend coverage. Dependency auditing reports no known vulnerabilities. The local E2E checker passed 10 scenarios. Two scenarios remain explicitly unverified: unknown-question behavior and document-grounded answering require Student 1's real AI. Docker Compose verification also remains to be run on a machine with Docker.

## Known limitations

- Student 1's real AI service is not running in this sandbox. Dummy mode validates transport, persistence, and UI contract behavior only; it does not validate semantic language detection, retrieval, confidence calibration, or grounding.
- Unknown/out-of-scope behavior is not claimed under dummy mode because the dummy always returns a sample source and confidence `1.0`.
- Document ingestion and document-grounded answering are not claimed under dummy mode; dummy ingestion reports pending.
- Docker Compose build, startup, restart persistence, image inspection, and container environment checks are **NOT RUN — Docker unavailable in sandbox**.
- Live AI-down and DB-down fault injection is not part of the local run; the adapter and centralized error paths are covered by automated tests.
- The rate limiter is process-local and in-memory. A multi-worker or horizontally scaled deployment should use a shared limiter store.
- The optional Docker AI service remains a commented placeholder until Student 1 confirms the image and endpoint contract.

## Architecture

The browser serves plain HTML/CSS/JavaScript from FastAPI at `/app`. API routes handle auth, chat, conversations, feedback, notices, admin operations, and document storage. SQLAlchemy persists application data in PostgreSQL. The backend calls one `ai_service` boundary that supports dummy, HTTP, and module adapters while preserving the stable request/response contract. Uploaded documents are validated and stored by the backend, then handed to Student 1's ingestion interface; embeddings, ChromaDB, chunking, retrieval, and LLM prompting remain outside this repository.
