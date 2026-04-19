"""FastAPI backend for the digital evidence integrity demo."""

from __future__ import annotations

import hashlib
import logging
import secrets
import tempfile
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from src import config
from src.case_id import CaseIdGenerationError, generate_case_id
from src.db import EvidenceRecord, SupabaseConfigError, SupabaseRepositoryError, get_repository, reset_repository_cache


app = FastAPI(title="Digital Evidence Integrity API", version="1.0.0")

cors_origins = [
    "http://localhost:5173",
    "https://blockchain-eta-taupe.vercel.app",
    "https://mini-ka-project.vercel.app",
]
if config.FRONTEND_URL:
    cors_origins.append(config.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    expose_headers=["X-Original-Hash", "X-Tampered-Hash", "X-Original-Filename", "Content-Disposition"],
)


_logger = logging.getLogger(__name__)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception) -> JSONResponse:
    _logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


def repository_dependency():
    try:
        return get_repository()
    except SupabaseConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _db_error(exc: SupabaseRepositoryError) -> HTTPException:
    reset_repository_cache()
    return HTTPException(status_code=500, detail=str(exc))


async def sha256_upload(file: UploadFile) -> str:
    digest = hashlib.sha256()
    total_bytes = 0

    while True:
        chunk = await file.read(config.CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        digest.update(chunk)

    if total_bytes == 0:
        raise HTTPException(status_code=400, detail="Uploaded file must not be empty")

    return digest.hexdigest()


async def _iter_spooled(f: tempfile.SpooledTemporaryFile, chunk_size: int):
    while True:
        chunk = f.read(chunk_size)
        if not chunk:
            break
        yield chunk


async def tamper_upload(file: UploadFile) -> tuple[tempfile.SpooledTemporaryFile[bytes], str, str]:
    original_digest = hashlib.sha256()
    tampered_digest = hashlib.sha256()
    total_bytes = 0
    output = tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024, mode="w+b")

    while True:
        chunk = await file.read(config.CHUNK_SIZE)
        if not chunk:
            break
        total_bytes += len(chunk)
        original_digest.update(chunk)
        tampered_digest.update(chunk)
        output.write(chunk)

    if total_bytes == 0:
        output.close()
        raise HTTPException(status_code=400, detail="Uploaded file must not be empty")

    tamper_bytes = secrets.token_bytes(secrets.randbelow(9) + 8)
    tampered_digest.update(tamper_bytes)
    output.write(tamper_bytes)
    output.seek(0)
    return output, original_digest.hexdigest(), tampered_digest.hexdigest()


def filename_for(file: UploadFile) -> str:
    return file.filename or "evidence.bin"


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "backend": "supabase",
        "app_version": "supabase-streaming-2026-04-20",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/evidence/register")
async def register_evidence(
    file: UploadFile = File(...),
    case_name: str = Form(...),
    repository=Depends(repository_dependency),
) -> dict[str, str | None]:
    file_hash = await sha256_upload(file)
    try:
        case_id = generate_case_id(case_name, repository)
        record = repository.insert(
            EvidenceRecord(
                case_id=case_id,
                file_hash=file_hash,
                original_filename=filename_for(file),
            )
        )
    except CaseIdGenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except SupabaseRepositoryError as exc:
        raise _db_error(exc) from exc

    return {
        "case_id": record.case_id,
        "file_hash": record.file_hash,
        "original_filename": record.original_filename,
        "timestamp": record.timestamp,
        "message": "Evidence registered. Save your case_id to verify later.",
    }


@app.post("/evidence/verify")
async def verify_evidence(
    file: UploadFile = File(...),
    case_id: str = Form(...),
    repository=Depends(repository_dependency),
) -> dict[str, str | None]:
    try:
        record = repository.fetch(case_id)
    except SupabaseRepositoryError as exc:
        raise _db_error(exc) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="case_id not found")

    submitted_hash = await sha256_upload(file)
    status = "INTACT" if submitted_hash == record.file_hash else "TAMPERED"
    return {
        "case_id": record.case_id,
        "status": status,
        "submitted_hash": submitted_hash,
        "stored_hash": record.file_hash,
        "original_filename": record.original_filename,
        "registered_at": record.timestamp,
    }


@app.post("/evidence/tamper")
async def tamper_evidence(file: UploadFile = File(...)) -> StreamingResponse:
    corrupted_file, original_hash, tampered_hash = await tamper_upload(file)
    original_filename = filename_for(file)
    download_name = f"tampered_{original_filename}"

    response = StreamingResponse(
        _iter_spooled(corrupted_file, config.CHUNK_SIZE),
        media_type=file.content_type or "application/octet-stream",
        background=BackgroundTask(corrupted_file.close),
    )
    response.headers["X-Original-Hash"] = original_hash
    response.headers["X-Tampered-Hash"] = tampered_hash
    response.headers["X-Original-Filename"] = original_filename
    safe_name = quote(download_name, safe="-_.~")
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{safe_name}"
    return response


@app.get("/evidence/list")
def list_evidence(repository=Depends(repository_dependency)) -> dict[str, object]:
    try:
        records = repository.list_records()
    except SupabaseRepositoryError as exc:
        raise _db_error(exc) from exc
    items = [
        {
            "case_id": record.case_id,
            "original_filename": record.original_filename,
            "timestamp": record.timestamp,
        }
        for record in records
    ]
    return {"total": len(items), "records": items}


@app.get("/evidence/{case_id}")
def get_evidence(case_id: str, repository=Depends(repository_dependency)) -> dict[str, str | None]:
    try:
        record = repository.fetch(case_id)
    except SupabaseRepositoryError as exc:
        raise _db_error(exc) from exc
    if record is None:
        raise HTTPException(status_code=404, detail="case_id not found")
    return record.to_api_dict()
