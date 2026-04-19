from pathlib import Path
from uuid import uuid4

import pytest

from src.chain_client import DuplicateRecordError, SqliteClient
from src.store_record import store_evidence
from src.verify_evidence import INTACT, verify_evidence


def workspace(name: str) -> Path:
    path = Path("test_runs") / name / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_sqlite_store_and_verify_round_trip() -> None:
    root = workspace("store-verify")
    evidence = root / "email.eml"
    evidence.write_text("original evidence", encoding="utf-8")
    client = SqliteClient(root / "ledger.sqlite")
    vault = root / "vault"

    stored = store_evidence(evidence, "CASE-TEST-1", client=client, vault_root=vault)
    verified = verify_evidence("CASE-TEST-1", client=client, vault_root=vault)

    assert stored["hash"] == verified["current_hash"]
    assert verified["stored_hash"] == verified["current_hash"]
    assert verified["status"] == INTACT


def test_sqlite_rejects_duplicate_case_id() -> None:
    root = workspace("store-verify")
    evidence = root / "email.eml"
    evidence.write_text("original evidence", encoding="utf-8")
    client = SqliteClient(root / "ledger.sqlite")
    vault = root / "vault"

    store_evidence(evidence, "CASE-DUPLICATE", client=client, vault_root=vault)

    with pytest.raises(DuplicateRecordError):
        store_evidence(evidence, "CASE-DUPLICATE", client=client, vault_root=vault)
