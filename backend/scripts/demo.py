"""Run the seven-step seminar demo end to end."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.chain_client import DuplicateRecordError, get_client  # noqa: E402
from src.config import DEFAULT_EVIDENCE_PATH, SAMPLE_EVIDENCE_PATH  # noqa: E402
from src.hash_evidence import sha256_file  # noqa: E402
from src.simulate_tampering import tamper_case  # noqa: E402
from src.store_record import store_evidence  # noqa: E402
from src.verify_evidence import INTACT, verify_evidence  # noqa: E402


def _evidence_file() -> Path:
    if DEFAULT_EVIDENCE_PATH.exists():
        return DEFAULT_EVIDENCE_PATH
    if SAMPLE_EVIDENCE_PATH.exists():
        return SAMPLE_EVIDENCE_PATH
    raise FileNotFoundError(f"Missing default evidence file: {DEFAULT_EVIDENCE_PATH}")


def _unique_case_id(base_case_id: str, client) -> str:
    if client.fetch(base_case_id) is None:
        return base_case_id
    return f"{base_case_id}-{int(time.time())}"


def run_demo(case_id: str, backend: str | None = None) -> int:
    client = get_client(backend)
    evidence_file = _evidence_file()
    case_id = _unique_case_id(case_id, client)

    print("Blockchain-Based Digital Evidence Integrity Demo")
    print(f"Backend selected: {client.backend_name}")
    print()

    print(f"[Step 1] Collected: {evidence_file}")
    digest = sha256_file(evidence_file)
    print(f"[Step 2] SHA-256:  {digest}")

    try:
        stored = store_evidence(evidence_file, case_id, client=client)
    except DuplicateRecordError:
        case_id = f"{case_id}-{int(time.time())}"
        stored = store_evidence(evidence_file, case_id, client=client)

    print(f"[Step 3] On-chain: {stored['tx_hash']} ({stored['backend']})")
    print(f"[Step 4] Vaulted:  {stored['vault_path']}")

    print("[Step 5] Verify... re-hashed")
    verified = verify_evidence(case_id, client=client)
    marker = "OK" if verified["status"] == INTACT else "ALERT"
    print(f"[Step 6] {marker} {verified['status']}")
    print(f"         Stored:  {verified['stored_hash']}")
    print(f"         Current: {verified['current_hash']}")
    print()

    tampered = tamper_case(case_id, client=client)
    print("--- simulating tampering ---")
    print(f"[Step 7] ALERT {tampered['status']}")
    print(f"         Before:  {tampered['before_hash']}")
    print(f"         After:   {tampered['after_hash']}")
    print(f"         Ledger:  {tampered['stored_hash']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the full seven-step seminar demo.")
    parser.add_argument("--case-id", default="CASE-001", help="Base case identifier for the demo")
    parser.add_argument("--backend", choices=["auto", "sqlite", "web3"], default=None)
    args = parser.parse_args(argv)
    return run_demo(args.case_id, args.backend)


if __name__ == "__main__":
    raise SystemExit(main())
