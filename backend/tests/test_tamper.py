from pathlib import Path
from uuid import uuid4

from src.chain_client import SqliteClient
from src.simulate_tampering import tamper_case
from src.store_record import store_evidence
from src.verify_evidence import TAMPERED


def workspace(name: str) -> Path:
    path = Path("test_runs") / name / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_tamper_case_changes_hash_and_reports_alert() -> None:
    root = workspace("tamper")
    evidence = root / "log.txt"
    evidence.write_text("server log line 1\n", encoding="utf-8")
    client = SqliteClient(root / "ledger.sqlite")
    vault = root / "vault"

    store_evidence(evidence, "CASE-TAMPER", client=client, vault_root=vault)
    result = tamper_case("CASE-TAMPER", client=client, vault_root=vault)

    assert result["status"] == TAMPERED
    assert result["before_hash"] != result["after_hash"]
    assert result["stored_hash"] == result["before_hash"]
