"""Tamper with vaulted evidence and show the verification alert."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .chain_client import ChainClient, get_client
from .hash_evidence import sha256_file
from .vault import get_vaulted_file
from .verify_evidence import print_verify_result, verify_evidence


def tamper_case(
    case_id: str,
    client: ChainClient | None = None,
    vault_root: Path | str | None = None,
) -> dict[str, Any]:
    evidence_path = get_vaulted_file(case_id) if vault_root is None else get_vaulted_file(case_id, vault_root=vault_root)
    before_hash = sha256_file(evidence_path)

    with evidence_path.open("ab") as handle:
        handle.write(b"\n# tampered-byte\n")

    after_hash = sha256_file(evidence_path)
    result = verify_evidence(case_id, evidence_path, client=client, vault_root=vault_root)
    result["before_hash"] = before_hash
    result["after_hash"] = after_hash
    return result


def print_tamper_result(result: dict[str, Any]) -> None:
    print("--- simulating tampering ---")
    print(f"Case ID:     {result['case_id']}")
    print(f"Before hash: {result['before_hash']}")
    print(f"After hash:  {result['after_hash']}")
    print()
    print_verify_result(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append one marker byte sequence to vaulted evidence.")
    parser.add_argument("case_id", help="Human-readable case identifier")
    parser.add_argument("--backend", choices=["auto", "sqlite", "web3"], default=None)
    args = parser.parse_args(argv)

    result = tamper_case(args.case_id, client=get_client(args.backend))
    print_tamper_result(result)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
