"""Compile and deploy EvidenceLedger.sol to a local Ganache chain."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import GANACHE_URL  # noqa: E402


def deploy() -> dict[str, object]:
    try:
        from solcx import compile_files, install_solc, set_solc_version
        from web3 import Web3
    except ImportError as exc:
        raise SystemExit("Install requirements first: pip install -r requirements.txt") from exc

    contract_path = ROOT / "contracts" / "EvidenceLedger.sol"
    install_solc("0.8.20")
    set_solc_version("0.8.20")
    compiled = compile_files([str(contract_path)], output_values=["abi", "bin"])
    contract_id = next(key for key in compiled if key.endswith(":EvidenceLedger"))
    interface = compiled[contract_id]

    w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
    if not w3.is_connected():
        raise SystemExit(f"Ganache is not reachable at {GANACHE_URL}")

    account = w3.eth.accounts[0]
    contract = w3.eth.contract(abi=interface["abi"], bytecode=interface["bin"])
    tx_hash = contract.constructor().transact({"from": account})
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    artifact = {
        "contractName": "EvidenceLedger",
        "address": receipt.contractAddress,
        "abi": interface["abi"],
        "transactionHash": receipt.transactionHash.hex(),
        "ganacheUrl": GANACHE_URL,
    }
    build_dir = ROOT / "build"
    build_dir.mkdir(exist_ok=True)
    (build_dir / "EvidenceLedger.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return artifact


def main() -> int:
    artifact = deploy()
    print("EvidenceLedger deployed")
    print(f"  Address: {artifact['address']}")
    print(f"  Tx hash: {artifact['transactionHash']}")
    print()
    print("Use this address for Web3 mode:")
    print(f"  $env:EVIDENCE_CONTRACT_ADDRESS = \"{artifact['address']}\"")
    print("  $env:EVIDENCE_BACKEND = \"web3\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

