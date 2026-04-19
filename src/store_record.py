"""Store a digital evidence hash in the configured ledger backend."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .chain_client import ChainClient, DuplicateRecordError, get_client
from .config import DEFAULT_EVIDENCE_PATH
from .hash_evidence import sha256_file
from .vault import store_file


def store_evidence(
    file_path: Path | str,
    case_id: str,
    client: ChainClient | None = None,
    vault_root: Path | str | None = None,
) -> dict[str, Any]:
    source = Path(file_path)
    digest = sha256_file(source)
    ledger = client or get_client()
    if ledger.fetch(case_id) is not None:
        raise DuplicateRecordError(f"Case already recorded: {case_id}")

    vaulted_path = store_file(case_id, source) if vault_root is None else store_file(case_id, source, vault_root)
    record = ledger.store(case_id, digest)

    return {
        "case_id": case_id,
        "hash": digest,
        "vault_path": str(vaulted_path),
        "timestamp": record["timestamp"],
        "backend": record["backend"],
        "tx_hash": record.get("tx_hash"),
        "submitter": record.get("submitter"),
    }


def print_store_result(result: dict[str, Any]) -> None:
    print("Evidence record stored")
    print(f"  Case ID:   {result['case_id']}")
    print(f"  SHA-256:   {result['hash']}")
    print(f"  Vaulted:   {result['vault_path']}")
    print(f"  Backend:   {result['backend']}")
    print(f"  Timestamp: {result['timestamp']}")
    print(f"  Tx/Record: {result['tx_hash']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hash, vault, and register evidence.")
    parser.add_argument("case_id", help="Human-readable case identifier")
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        default=DEFAULT_EVIDENCE_PATH,
        help="Path to the evidence file; defaults to ./evidence",
    )
    parser.add_argument("--backend", choices=["auto", "sqlite", "web3"], default=None)
    args = parser.parse_args(argv)

    result = store_evidence(args.file, args.case_id, client=get_client(args.backend))
    print_store_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
