# Phase 18 — Final End-to-End Test Report

**Project:** SIH25104 Language-Agnostic Institutional Chatbot  
**Environment:** Local sandbox, FastAPI on `http://127.0.0.1:8000`, PostgreSQL reachable, `AI_MODE=dummy`  
**Date:** 2026-10-15  

## E2E scenario results

The E2E checker was run with:

```bash
set -a && . ./.env && set +a
python scripts/e2e_check.py http://127.0.0.1:8000
```

The checker created a uniquely tagged student account, logged in as the configured admin, ran the scenarios, deleted the uploaded document through the API, and removed the temporary student's conversations and account through a scoped database cleanup. The configured admin account was not deleted.

| # | Scenario | Input | Expected | Actual result | Status |
|---:|---|---|---|---|---|
| 1 | English question | `How do I apply for a scholarship?` | HTTP 200 with the stable AI response contract | HTTP 200; `language='hinglish'`, `confidence=1.0`; dummy AI returned the response, so semantic language detection was not validated | **PASS** |
| 2 | Hindi (Devanagari) question | `छात्रवृत्ति के लिए आवेदन कैसे करें?` | HTTP 200 with the stable AI response contract | HTTP 200; `language='hinglish'`, `confidence=1.0`; dummy AI returned the response, so semantic language detection was not validated | **PASS** |
| 3 | Hinglish question | `Scholarship ke liye eligibility kya hai?` | HTTP 200 with the stable AI response contract | HTTP 200; `language='hinglish'`, `confidence=1.0`; dummy AI returned the response, so semantic language detection was not validated | **PASS** |
| 4 | Code-mixed question | `What documents chahiye for hostel admission?` | HTTP 200 with the stable AI response contract | HTTP 200; `language='hinglish'`, `confidence=1.0`; dummy AI returned the response, so semantic language detection was not validated | **PASS** |
| 5 | Follow-up depending on the previous turn | First question followed by `And what is the required format?` in the same conversation | Previous turn included in the AI history payload | HTTP 200; dummy response reported `received 1 previous turn` | **PASS** |
| 6 | Unknown/out-of-scope question | `What is the admission policy for a university on Mars?` | Low confidence or no sources; no fabricated source | Dummy AI always returns `sample_document.pdf`, page 1, section `Demo`, confidence `1.0` | **NOT RUN — needs Student 1's AI** |
| 7 | Source display | Request to return document/page/section metadata | Source fields returned exactly as provided | HTTP 200; sources exactly returned as `sample_document.pdf`, page 1, section `Demo` | **PASS** |
| 8 | Conversation history | Logged-in student's saved conversation | List and detail restore the conversation and messages | HTTP 200; conversation appeared in the list and restored detail contained messages | **PASS** |
| 9 | Admin upload, ingestion, and document-grounded answer | Upload unique TXT document, then ask a related question | Document is ingested and answer is grounded in that document | Upload HTTP 201 with `ingestion_status='pending'`; document-grounded question was not run against a real ingestion/retrieval service | **NOT RUN — needs Student 1's AI** |
| 10 | Positive and negative feedback in admin dashboard | Submit one positive and one negative feedback entry | Both values visible in admin feedback results | HTTP 200; admin feedback included positive and negative entries | **PASS** |
| 11 | Authentication and role checks | Student requests `/admin/stats`; guest posts `/chat` | Student receives 403; guest chat succeeds | Student admin access HTTP 403; guest chat HTTP 200 | **PASS** |
| 12 | Error handling | Invalid `.exe` upload; 20,000-byte `/chat` body | Friendly invalid-file and oversized-body errors; AI/DB failures separately checked | Invalid file HTTP 400; oversized message HTTP 413; AI-down and DB-down fault injection were not run | **PASS for checks run; AI/DB fault injection NOT RUN** |

### E2E command output

```text
PASS: 1. English question — HTTP 200; language='hinglish', confidence=1.0; run against AI_MODE=dummy, so semantic language detection is not validated
PASS: 2. Hindi (Devanagari) question — HTTP 200; language='hinglish', confidence=1.0; run against AI_MODE=dummy, so semantic language detection is not validated
PASS: 3. Hinglish question — HTTP 200; language='hinglish', confidence=1.0; run against AI_MODE=dummy, so semantic language detection is not validated
PASS: 4. Code-mixed question — HTTP 200; language='hinglish', confidence=1.0; run against AI_MODE=dummy, so semantic language detection is not validated
PASS: 5. Follow-up question that depends on the previous turn — HTTP 200; dummy AI reported received 1 previous turn
NOT RUN: 6. Unknown/out-of-scope question — NOT RUN — needs Student 1's AI; dummy always returns a sample source and confidence 1.0
PASS: 7. Source display — HTTP 200; sources exactly as returned: [{'document': 'sample_document.pdf', 'page': 1, 'section': 'Demo'}]
PASS: 8. Conversation history — HTTP 200; conversation appears in list and restored detail contains messages
NOT RUN: 9. Admin document upload -> ingestion -> question grounded in document — Upload HTTP 201 with ingestion_status='pending'; question grounding NOT RUN — needs Student 1's AI
PASS: 10. Positive and negative feedback visible in admin dashboard — HTTP 200; admin feedback includes positive and negative entries
PASS: 11. Authentication and role checks — Student admin access HTTP 403; guest chat HTTP 200
PASS: 12. Error handling — Invalid file HTTP 400; oversized message HTTP 413; AI-down and DB-down fault injection NOT RUN
SUMMARY: 10 PASS, 0 FAIL, 2 NOT RUN
```

## Automated and security verification

Final test command:

```bash
pytest -q && python -m compileall -q backend scripts && pip-audit -r requirements.txt
```

Observed output:

```text
42 passed in 12.20s
No known vulnerabilities found
```

Phase 15 security smoke checks were rerun:

```text
Phase 15 smoke checks passed
```

The checks covered security headers, allowed and blocked CORS preflight requests, and oversized `/chat` rejection.

Additional final checks passed:

```text
git hygiene: no tracked .env or uploads paths
fresh venv requirements install and backend compile: passed
```

A clean GitHub clone was also started with the README's non-Docker command path and returned:

```json
{"status":"ok"}
```

## Not tested in this sandbox

- `docker compose down -v` and `docker compose up --build`: **NOT RUN — Docker unavailable in sandbox**. Docker was not installed (`docker: command not found`) during Phase 17 and remains unverified here.
- Docker persistence across restart: **NOT RUN — Docker unavailable in sandbox**.
- Docker image secret inspection and `docker compose exec backend env`: **NOT RUN — Docker unavailable in sandbox**.
- Student 1's real HTTP/module AI, semantic language detection, unknown-question confidence behavior, document ingestion, retrieval, and document-grounded answering: **NOT RUN — needs Student 1's AI**.
- AI-down and DB-down live fault injection: **NOT RUN** because it requires deliberately changing or stopping external services during the live run.

## Exact commands to close remaining gaps

From the repository root, after installing Docker and preparing `.env`:

```bash
docker compose down -v
docker compose up --build
```

In another terminal:

```bash
set -a && . ./.env && set +a
python scripts/e2e_check.py http://localhost:8000
```

When Student 1's AI service is ready, set the agreed adapter variables in `.env`:

```env
AI_MODE=http
AI_BASE_URL=http://ai:8001
```

Then rerun the same E2E command and specifically review scenarios 6 and 9. Do not use `AI_MODE=dummy` to claim those scenarios are validated.
