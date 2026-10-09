# AI integration contract

Phase 11 gives the backend one stable boundary in
`backend/services/ai_service.py`. The backend does not access ChromaDB,
embeddings, chunking, retrieval, or prompts. Those remain Student 1's
responsibility.

## Stable answer contract

Backend to AI:

```json
{
  "conversation_id": "abc123",
  "message": "Scholarship ki eligibility kya hai?",
  "history": [
    {"user": "...", "assistant": "..."}
  ]
}
```

AI to backend:

```json
{
  "answer": "...",
  "language": "hinglish",
  "sources": [
    {"document": "scholarship.pdf", "page": 3, "section": "Eligibility"}
  ],
  "confidence": 0.91
}
```

The backend validates the response strictly: `answer` and `language` must be
strings, `sources` must contain the contract source objects, and `confidence`
must be between `0` and `1`. Invalid output becomes a `502` response and is
never sent to the browser or saved to PostgreSQL.

## Adapter selection

Set `AI_MODE` in `.env`:

| Mode | Configuration | Behavior |
| --- | --- | --- |
| `dummy` | No extra setting | Development/test only. Refused in production and logs a loud startup warning. |
| `http` | `AI_BASE_URL` | Calls the HTTP adapter described below. |
| `module` | `AI_MODULE_PATH` | Imports the configured dotted Python module. |

`AI_TIMEOUT_SECONDS` applies to HTTP calls. The example defaults to `30`.

### HTTP adapter placeholder paths

The current reasonable placeholder paths are:

- `POST {AI_BASE_URL}/answer` with the exact answer request JSON.
- `POST {AI_BASE_URL}/ingest` as multipart upload with `document_id` and `original_filename`.
- `DELETE {AI_BASE_URL}/documents/{document_id}`.

These endpoint paths are **not finalized** with Student 1. They are isolated in
`backend/services/ai_service.py` and can be changed there without changing the
rest of the backend contract. Student 1 and Student 2 must confirm exact paths,
request encoding, response status codes, and error semantics before enabling
this adapter in a shared environment.

### Module adapter

`AI_MODULE_PATH` points to a module exposing:

```python
def answer(message: str, conversation_id: str, history: list[dict]) -> dict:
    ...

def ingest_document(file_path: str, document_id: int, original_filename: str) -> dict:
    ...

def delete_document(document_id: int, original_filename: str) -> dict:
    ...
```

Answer results must use the stable AI response contract. Ingestion results use
`{"status": "ingested"|"failed"|"pending", "error": str|None}` and delete
results use `{"status": "deleted"|"failed"|"pending", "error": str|None}`.

## Error mapping

- AI connection refusal, non-2xx, or unavailable module: `503`
- AI timeout: `504`
- Malformed AI response: `502`

Failed chat requests roll back the current database session; no user message,
assistant message, response, or source is persisted.

## Documents

Document upload keeps the file and records `pending` or `failed` ingestion
status. Admins can retry with `POST /documents/{id}/reingest`. Local file
storage is deleted only after the delete adapter call is attempted; any AI-side
failure is returned as a warning while local database/file deletion still
proceeds.

## Health check

`GET /health/ai` returns an `ok` or `unavailable` status without crashing the
application. Dummy mode reports `ok` with `mode: dummy`; HTTP mode performs a
cheap base-URL reachability check; module mode loads the configured module and
calls its optional `health()` function when present.

## Student 1 integration checklist

1. Agree on HTTP paths or provide the module path and exact function signatures.
2. Confirm the answer response field names and source field types exactly.
3. Confirm ingestion/delete status and retry/idempotency behavior.
4. Run a valid answer with one previous history turn.
5. Run a malformed answer and confirm backend returns `502`.
6. Stop the AI service and confirm backend returns `503` without a DB row.
7. Delay the AI beyond `AI_TIMEOUT_SECONDS` and confirm `504`.
8. Upload a document, confirm ingestion status, retry it, and delete it.
9. Check `GET /health/ai` from both sides before enabling production traffic.
