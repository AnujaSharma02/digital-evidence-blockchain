"""Verify vaulted evidence by comparing current and stored hashes."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .chain_client import ChainClient, get_client
from .hash_evidence import sha256_file
from .vault import get_vaulted_file

INTACT = "INTACT"
TAMPERED = "TAMPERED"
MISSING = "MISSING"


def verify_evidence(
    case_id: str,
    file_path: Path | str | None = None,
    client: ChainClient | None = None,
    vault_root: Path | str | None = None,
) -> dict[str, Any]:
    ledger = client or get_client()
    record = ledger.fetch(case_id)
    if record is None:
        return {
            "case_id": case_id,
            "status": MISSING,
            "stored_hash": None,
            "current_hash": None,
            "backend": getattr(ledger, "backend_name", "unknown"),
            "file_path": str(file_path) if file_path is not None else None,
        }

    if file_path is not None:
        evidence_path = Path(file_path)
    elif vault_root is None:
        evidence_path = get_vaulted_file(case_id)
    else:
        evidence_path = get_vaulted_file(case_id, vault_root=vault_root)
    current_hash = sha256_file(evidence_path)
    stored_hash = record["file_hash"]
    status = INTACT if current_hash == stored_hash else TAMPERED

    return {
        "case_id": case_id,
        "status": status,
        "stored_hash": stored_hash,
        "current_hash": current_hash,
        "backend": record["backend"],
        "file_path": str(evidence_path),
        "timestamp": record["timestamp"],
        "submitter": record.get("submitter"),
    }


def print_verify_result(result: dict[str, Any]) -> None:
    print(f"Verification result for {result['case_id']}: {result['status']}")
    print(f"  Backend:      {result['backend']}")
    print(f"  File:         {result['file_path']}")
    print(f"  Stored hash:  {result['stored_hash']}")
    print(f"  Current hash: {result['current_hash']}")
    if result["status"] == INTACT:
        print("  Decision:     Evidence is intact.")
    elif result["status"] == TAMPERED:
        print("  Decision:     TAMPERING DETECTED.")
    else:
        print("  Decision:     No ledger record found.")


def exit_code_for_status(status: str) -> int:
    if status == INTACT:
        return 0
    if status == TAMPERED:
        return 2
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify evidence integrity against the ledger.")
    parser.add_argument("case_id", help="Human-readable case identifier")
    parser.add_argument("file", nargs="?", type=Path, help="Optional file path; defaults to vaulted file")
    parser.add_argument("--backend", choices=["auto", "sqlite", "web3"], default=None)
    args = parser.parse_args(argv)

    result = verify_evidence(args.case_id, args.file, client=get_client(args.backend))
    print_verify_result(result)
    return exit_code_for_status(result["status"])


if __name__ == "__main__":
    raise SystemExit(main())
