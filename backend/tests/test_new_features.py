"""Additional pytest tests for the FastAPI blockchain evidence backend.

Covers behaviors not present in test_endpoints.py:
  - Empty file rejection on /register, /verify, /tamper
  - tamper_upload hash consistency with a 1 MB payload
  - Full round-trip: register -> tamper -> verify returns TAMPERED
  - Unknown CORS origin is not echoed back
  - SupabaseRepositoryError in verify_evidence returns 500
  - /evidence/list returns empty list when no records exist
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from main import app, repository_dependency
from tests.helpers import sha256_bytes
from src.db import EvidenceRecord, SupabaseRepositoryError


# ---------------------------------------------------------------------------
# Shared test infrastructure (mirrors the pattern in test_endpoints.py)
# ---------------------------------------------------------------------------

class FakeRepository:
    """In-memory repository that satisfies the same interface as
    SupabaseEvidenceRepository without touching any external service."""

    def __init__(self) -> None:
        self.records: dict[str, EvidenceRecord] = {}
        self.candidate_exists = False

    def exists(self, case_id: str) -> bool:
        return self.candidate_exists or case_id in self.records

    def insert(self, record: EvidenceRecord) -> EvidenceRecord:
        stored = replace(record, timestamp="2026-04-19T10:30:00Z")
        self.records[stored.case_id] = stored
        return stored

    def fetch(self, case_id: str) -> EvidenceRecord | None:
        return self.records.get(case_id)

    def list_records(self) -> list[EvidenceRecord]:
        return list(self.records.values())


def client_with(repository: FakeRepository) -> TestClient:
    app.dependency_overrides[repository_dependency] = lambda: repository
    return TestClient(app)


def clear_overrides() -> None:
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. Empty file rejection
# ---------------------------------------------------------------------------

class TestEmptyFileRejection:
    """POST endpoints must return 400 when the uploaded file body is empty."""

    def test_register_empty_file_returns_400(self) -> None:
        repository = FakeRepository()
        client = client_with(repository)

        response = client.post(
            "/evidence/register",
            data={"case_name": "Empty File Case"},
            files={"file": ("empty.bin", b"", "application/octet-stream")},
        )
        clear_overrides()

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_verify_empty_file_returns_400(self) -> None:
        repository = FakeRepository()
        # Seed a real record so the case_id lookup succeeds before the
        # empty-file check would even be reached.
        repository.records["case-empty"] = EvidenceRecord(
            case_id="case-empty",
            file_hash=sha256_bytes(b"some original content"),
            original_filename="doc.pdf",
            timestamp="2026-04-19T10:30:00Z",
        )
        client = client_with(repository)

        response = client.post(
            "/evidence/verify",
            data={"case_id": "case-empty"},
            files={"file": ("doc.pdf", b"", "application/pdf")},
        )
        clear_overrides()

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_tamper_empty_file_returns_400(self) -> None:
        client = TestClient(app)

        response = client.post(
            "/evidence/tamper",
            files={"file": ("empty.bin", b"", "application/octet-stream")},
        )

        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 2. tamper_upload hash consistency — 1 MB stress test
# ---------------------------------------------------------------------------

class TestTamperHashConsistency:
    """X-Tampered-Hash must equal sha256(response.content) for any payload."""

    def test_tamper_hash_matches_body_for_1mb_payload(self) -> None:
        large_payload = os.urandom(1024 * 1024)  # 1 MB of random bytes
        client = TestClient(app)

        response = client.post(
            "/evidence/tamper",
            files={"file": ("big.bin", large_payload, "application/octet-stream")},
        )

        assert response.status_code == 200
        # The body must contain the original payload as a prefix
        assert response.content[:len(large_payload)] == large_payload
        # The body must be longer (tamper bytes were appended)
        assert len(response.content) > len(large_payload)
        # The hash declared in the header must match the actual body
        expected_hash = hashlib.sha256(response.content).hexdigest()
        assert response.headers["X-Tampered-Hash"] == expected_hash
        # The original hash header must match the original payload
        assert response.headers["X-Original-Hash"] == sha256_bytes(large_payload)


# ---------------------------------------------------------------------------
# 3. Full round-trip: register -> tamper -> verify returns TAMPERED
# ---------------------------------------------------------------------------

class TestTamperedFileFailsVerification:
    """After tampering a registered file, verification must report TAMPERED."""

    def test_round_trip_register_tamper_verify_returns_tampered(self) -> None:
        original_bytes = b"sensitive court document content that must not change"
        repository = FakeRepository()
        client = client_with(repository)

        # Step 1 — register the original file
        register_response = client.post(
            "/evidence/register",
            data={"case_name": "Round Trip Tamper Test"},
            files={"file": ("evidence.pdf", original_bytes, "application/pdf")},
        )
        assert register_response.status_code == 200
        case_id = register_response.json()["case_id"]

        # Step 2 — corrupt the same bytes via /evidence/tamper
        tamper_response = client.post(
            "/evidence/tamper",
            files={"file": ("evidence.pdf", original_bytes, "application/pdf")},
        )
        assert tamper_response.status_code == 200
        corrupted_bytes = tamper_response.content

        # Sanity: tampered bytes differ from original
        assert corrupted_bytes != original_bytes

        # Step 3 — verify the corrupted file against the registered case_id
        verify_response = client.post(
            "/evidence/verify",
            data={"case_id": case_id},
            files={"file": ("evidence.pdf", corrupted_bytes, "application/pdf")},
        )
        clear_overrides()

        body = verify_response.json()
        assert verify_response.status_code == 200
        assert body["status"] == "TAMPERED"
        assert body["submitted_hash"] != body["stored_hash"]
        assert body["submitted_hash"] == sha256_bytes(corrupted_bytes)


# ---------------------------------------------------------------------------
# 4. Unknown CORS origin is not reflected
# ---------------------------------------------------------------------------

class TestCORSUnknownOriginRejected:
    """An origin not in the allow-list must not appear in the CORS response."""

    @pytest.mark.parametrize("evil_origin", [
        "https://evil.com",
        "https://attacker.io",
        "http://localhost:9999",
        "https://notvercel.app",
    ])
    def test_unknown_origin_not_allowed_by_cors(self, evil_origin: str) -> None:
        client = TestClient(app)

        response = client.options(
            "/evidence/register",
            headers={
                "Origin": evil_origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        # The CORS middleware must NOT echo back the attacker's origin.
        acao = response.headers.get("access-control-allow-origin", "")
        assert acao != evil_origin, (
            f"Expected origin '{evil_origin}' to be blocked, "
            f"but 'access-control-allow-origin' was '{acao}'"
        )


# ---------------------------------------------------------------------------
# 5. SupabaseRepositoryError in verify_evidence returns 500
# ---------------------------------------------------------------------------

class FakeRepositoryFetchRaises(FakeRepository):
    """Variant that raises SupabaseRepositoryError on every fetch() call."""

    def fetch(self, case_id: str) -> EvidenceRecord | None:
        raise SupabaseRepositoryError("Simulated Supabase fetch failure")


class TestVerifyEvidenceRepositoryError:
    """When the repository raises SupabaseRepositoryError, the endpoint
    must return 500 with a descriptive error detail."""

    def test_supabase_repository_error_in_verify_returns_500(self) -> None:
        repository = FakeRepositoryFetchRaises()
        client = client_with(repository)

        response = client.post(
            "/evidence/verify",
            data={"case_id": "any-case"},
            files={"file": ("doc.txt", b"some content", "text/plain")},
        )
        clear_overrides()

        assert response.status_code == 500
        detail = response.json()["detail"]
        assert "Simulated Supabase fetch failure" in detail


# ---------------------------------------------------------------------------
# 6. /evidence/list returns empty list when no records exist
# ---------------------------------------------------------------------------

class TestListEvidenceEmpty:
    """/evidence/list must return total=0 and records=[] when the repository
    holds no records."""

    def test_list_returns_empty_when_no_records(self) -> None:
        repository = FakeRepository()  # empty by default
        client = client_with(repository)

        response = client.get("/evidence/list")
        clear_overrides()

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert body["records"] == []
