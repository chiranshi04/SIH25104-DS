"""Safe document storage helpers; chunking/embeddings are intentionally excluded."""

import hashlib
import re
import uuid
import zipfile
from codecs import getincrementaldecoder
from pathlib import Path

from fastapi import UploadFile

from backend.config import settings

ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    },
    ".txt": {"text/plain"},
}
CHUNK_SIZE = 1024 * 1024


def upload_root() -> Path:
    path = Path(settings.UPLOAD_DIR).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def clean_original_filename(filename: str | None) -> str:
    name = Path(filename or "document").name
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:255] or "document"


def extension_for(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_reported_type(extension: str, content_type: str | None) -> None:
    if extension not in ALLOWED_MIME_TYPES:
        raise ValueError("Only .pdf, .docx, and .txt files are allowed")
    if (content_type or "").lower() not in ALLOWED_MIME_TYPES[extension]:
        raise ValueError("Reported MIME type does not match the file extension")


def validate_magic(path: Path, extension: str) -> None:
    if extension == ".pdf":
        with path.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise ValueError("File magic bytes do not match PDF")
    elif extension == ".docx":
        try:
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
                if "[Content_Types].xml" not in names or not any(
                    name == "word/" or name.startswith("word/") for name in names
                ):
                    raise ValueError("DOCX package is missing required files")
        except zipfile.BadZipFile as exc:
            raise ValueError("DOCX file is not a valid ZIP package") from exc
    else:
        decoder = getincrementaldecoder("utf-8")()
        with path.open("rb") as handle:
            while chunk := handle.read(CHUNK_SIZE):
                if b"\x00" in chunk:
                    raise ValueError("TXT files must not contain NUL bytes")
                try:
                    decoder.decode(chunk)
                except UnicodeDecodeError as exc:
                    raise ValueError("TXT file must be valid UTF-8") from exc
        try:
            decoder.decode(b"", final=True)
        except UnicodeDecodeError as exc:
            raise ValueError("TXT file must be valid UTF-8") from exc


async def stream_to_disk(upload: UploadFile, destination: Path, max_bytes: int) -> tuple[int, str]:
    size = 0
    digest = hashlib.sha256()
    with destination.open("wb") as handle:
        while chunk := await upload.read(CHUNK_SIZE):
            size += len(chunk)
            if size > max_bytes:
                raise OverflowError("Document exceeds the configured upload size limit")
            handle.write(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def remove_file(stored_filename: str) -> None:
    candidate = (upload_root() / stored_filename).resolve()
    root = upload_root()
    if candidate.parent != root:
        return
    candidate.unlink(missing_ok=True)
