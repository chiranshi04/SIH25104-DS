from io import BytesIO
import zipfile
from pathlib import Path

from backend.config import settings
from backend.database.models import Document


def pdf_bytes():
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"


def docx_bytes():
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    return output.getvalue()


def upload(client, token, filename, content, content_type):
    return client.post(
        "/documents/upload",
        files={"file": (filename, content, content_type)},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_valid_pdf_docx_txt_uploads(client, admin_token, fake_ai):
    cases = [
        ("guide.pdf", pdf_bytes(), "application/pdf"),
        (
            "guide.docx",
            docx_bytes(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("guide.txt", b"hello UTF-8", "text/plain"),
    ]
    for filename, content, content_type in cases:
        response = upload(client, admin_token, filename, content, content_type)
        assert response.status_code == 201, response.text
        assert response.json()["original_filename"] == filename
        assert response.json()["ingestion_status"] == "ingested"


def test_invalid_extension_and_mime_mismatch(client, admin_token):
    assert upload(client, admin_token, "bad.exe", b"MZ", "application/octet-stream").status_code == 400
    mismatch = upload(client, admin_token, "bad.pdf", b"not pdf", "text/plain")
    assert mismatch.status_code == 400
    assert "MIME" in mismatch.json()["detail"]


def test_empty_bad_magic_and_oversized_files_leave_no_file(client, admin_token, monkeypatch):
    empty = upload(client, admin_token, "empty.txt", b"", "text/plain")
    assert empty.status_code == 400
    bad_magic = upload(client, admin_token, "bad.pdf", b"not pdf", "application/pdf")
    assert bad_magic.status_code == 400
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 0)
    oversized = upload(client, admin_token, "large.txt", b"x", "text/plain")
    assert oversized.status_code == 413
    assert not list(Path(settings.UPLOAD_DIR).glob("*"))


def test_duplicate_and_path_traversal_filename(client, admin_token):
    first = upload(client, admin_token, "../safe.txt", b"unique-content", "text/plain")
    assert first.status_code == 201
    assert first.json()["original_filename"] == "safe.txt"
    duplicate = upload(client, admin_token, "copy.txt", b"unique-content", "text/plain")
    assert duplicate.status_code == 409
    listed = client.get("/documents", headers={"Authorization": f"Bearer {admin_token}"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_delete_removes_database_row_and_file(client, db_session, admin_token):
    created = upload(client, admin_token, "delete.txt", b"delete me", "text/plain")
    document_id = created.json()["id"]
    stored = db_session.get(Document, document_id).stored_filename
    path = Path(settings.UPLOAD_DIR) / stored
    assert path.exists()
    deleted = client.delete(
        f"/documents/{document_id}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert deleted.status_code == 200
    assert db_session.get(Document, document_id) is None
    assert not path.exists()


def test_student_cannot_upload_or_delete(client, student_token):
    headers = {"Authorization": f"Bearer {student_token}"}
    assert upload(client, student_token, "x.txt", b"x", "text/plain").status_code == 403
    assert client.delete("/documents/1", headers=headers).status_code == 403


def test_ingestion_failure_keeps_file(client, admin_token, db_session, fake_ai):
    fake_ai.ingestion_mode = "failure"
    response = upload(client, admin_token, "failure.txt", b"keep me", "text/plain")
    assert response.status_code == 201
    body = response.json()
    assert body["ingestion_status"] == "failed"
    assert body["ingestion_error"] == "fake ingestion failed"
    document = db_session.get(Document, body["id"])
    assert document is not None
    assert (Path(settings.UPLOAD_DIR) / document.stored_filename).exists()


def test_reingest_existing_and_missing_file(client, admin_token, db_session, fake_ai):
    created = upload(client, admin_token, "reingest.txt", b"reingest", "text/plain")
    document_id = created.json()["id"]
    response = client.post(
        f"/documents/{document_id}/reingest", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    document = db_session.get(Document, document_id)
    path = Path(settings.UPLOAD_DIR) / document.stored_filename
    path.unlink()
    missing = client.post(
        f"/documents/{document_id}/reingest", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert missing.status_code == 200
    assert missing.json()["ingestion_status"] == "failed"
    assert client.post(
        "/documents/9999/reingest", headers={"Authorization": f"Bearer {admin_token}"}
    ).status_code == 404


def test_delete_ai_failure_returns_warning(client, admin_token, monkeypatch):
    created = upload(client, admin_token, "warning.txt", b"warning", "text/plain")
    import backend.api.documents as documents_api

    def fail(*_args):
        raise RuntimeError("AI down")

    monkeypatch.setattr(documents_api.ingestion_service, "delete_document", fail)
    response = client.delete(
        f"/documents/{created.json()['id']}", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["warning"] == "AI-side document deletion failed"
    assert client.delete(
        "/documents/9999", headers={"Authorization": f"Bearer {admin_token}"}
    ).status_code == 404
