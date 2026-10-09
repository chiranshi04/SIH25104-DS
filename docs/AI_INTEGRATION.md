# AI ingestion integration boundary

Phase 10 deliberately does **not** implement chunking, embeddings, retrieval, or ChromaDB.
Those responsibilities belong to Student 1.

The backend currently calls these stub signatures from `backend/services/ingestion_service.py`:

```python
def ingest_document(file_path: str, document_id: int, original_filename: str) -> dict:
    # {"status": "ingested"|"failed"|"pending", "error": str|None}
    ...

def delete_document(document_id: int, original_filename: str) -> dict:
    # {"status": "deleted"|"failed"|"pending", "error": str|None}
    ...
```

The Phase 10 stubs return:

```text
status: pending
error: AI ingestion not connected yet
```

Before Phase 11, Student 1 and Student 2 must agree on the final signatures,
status values, error behavior, and retry/idempotency rules. Phase 11 will wire
the real ingestion implementation into this boundary.
