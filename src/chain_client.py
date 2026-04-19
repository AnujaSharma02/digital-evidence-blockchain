"""Blockchain and SQLite ledger backends behind one client interface."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Protocol

from . import config


class ChainClient(Protocol):
    backend_name: str

    def store(self, case_id: str, file_hash: str) -> dict[str, Any]:
        ...

    def fetch(self, case_id: str) -> dict[str, Any] | None:
        ...


class ChainClientError(RuntimeError):
    """Base error for ledger client failures."""


class DuplicateRecordError(ChainClientError):
    """Raised when an immutable evidence record already exists."""


class BackendUnavailableError(ChainClientError):
    """Raised when the requested ledger backend cannot be used."""


def normalize_hash(file_hash: str) -> str:
    digest = file_hash.lower().removeprefix("0x")
    if len(digest) != 64:
        raise ValueError("SHA-256 hash must be 64 hex characters")
    try:
        int(digest, 16)
    except ValueError as exc:
        raise ValueError("SHA-256 hash must be hexadecimal") from exc
    return digest


class SqliteClient:
    backend_name = "sqlite"

    def __init__(self, db_path: Path | str = config.SQLITE_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.execute("PRAGMA temp_store=MEMORY")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    case_id TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    ts INTEGER NOT NULL,
                    submitter TEXT NOT NULL
                )
                """
            )

    def store(self, case_id: str, file_hash: str) -> dict[str, Any]:
        digest = normalize_hash(file_hash)
        timestamp = int(time.time())
        submitter = "sqlite://local"

        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO records(case_id, file_hash, ts, submitter) VALUES (?, ?, ?, ?)",
                    (case_id, digest, timestamp, submitter),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateRecordError(f"Case already recorded: {case_id}") from exc

        return {
            "case_id": case_id,
            "file_hash": digest,
            "timestamp": timestamp,
            "submitter": submitter,
            "backend": self.backend_name,
            "tx_hash": f"sqlite:{case_id}:{timestamp}",
        }

    def fetch(self, case_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT case_id, file_hash, ts, submitter FROM records WHERE case_id = ?",
                (case_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "case_id": row["case_id"],
            "file_hash": row["file_hash"],
            "timestamp": row["ts"],
            "submitter": row["submitter"],
            "backend": self.backend_name,
            "tx_hash": None,
        }


EVIDENCE_LEDGER_ABI: list[dict[str, Any]] = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "internalType": "string", "name": "caseId", "type": "string"},
            {"indexed": False, "internalType": "bytes32", "name": "fileHash", "type": "bytes32"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "EvidenceStored",
        "type": "event",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "caseId", "type": "string"},
        ],
        "name": "getEvidence",
        "outputs": [
            {"internalType": "bytes32", "name": "", "type": "bytes32"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
            {"internalType": "address", "name": "", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "caseId", "type": "string"},
            {"internalType": "bytes32", "name": "fileHash", "type": "bytes32"},
        ],
        "name": "storeEvidence",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


class Web3Client:
    backend_name = "web3"

    def __init__(
        self,
        provider_url: str = config.GANACHE_URL,
        contract_address: str = config.CONTRACT_ADDRESS,
        abi: list[dict[str, Any]] = EVIDENCE_LEDGER_ABI,
    ) -> None:
        if not contract_address:
            raise BackendUnavailableError("EVIDENCE_CONTRACT_ADDRESS is not set")

        try:
            from web3 import Web3
            from web3.exceptions import ContractLogicError
        except ImportError as exc:
            raise BackendUnavailableError("web3 is not installed") from exc

        self._logic_error = ContractLogicError
        self.w3 = Web3(Web3.HTTPProvider(provider_url, request_kwargs={"timeout": 2}))
        if not self.w3.is_connected():
            raise BackendUnavailableError(f"Cannot connect to Ganache at {provider_url}")

        self.account = self.w3.eth.accounts[0]
        checksum_address = self.w3.to_checksum_address(contract_address)
        self.contract = self.w3.eth.contract(address=checksum_address, abi=abi)

    def store(self, case_id: str, file_hash: str) -> dict[str, Any]:
        digest = normalize_hash(file_hash)
        try:
            tx_hash = self.contract.functions.storeEvidence(case_id, bytes.fromhex(digest)).transact(
                {"from": self.account}
            )
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except self._logic_error as exc:
            message = str(exc)
            if "Case already recorded" in message:
                raise DuplicateRecordError(f"Case already recorded: {case_id}") from exc
            raise ChainClientError(message) from exc

        record = self.fetch(case_id)
        if record is None:
            raise ChainClientError("Transaction succeeded but record could not be fetched")

        record["tx_hash"] = receipt.transactionHash.hex()
        return record

    def fetch(self, case_id: str) -> dict[str, Any] | None:
        try:
            file_hash_bytes, timestamp, submitter = self.contract.functions.getEvidence(case_id).call()
        except self._logic_error:
            return None

        return {
            "case_id": case_id,
            "file_hash": file_hash_bytes.hex(),
            "timestamp": int(timestamp),
            "submitter": submitter,
            "backend": self.backend_name,
            "tx_hash": None,
        }


def get_client(backend: str | None = None) -> ChainClient:
    selected = (backend or config.BACKEND).lower()
    if selected == "sqlite":
        return SqliteClient()
    if selected == "web3":
        return Web3Client()
    if selected != "auto":
        raise ValueError("backend must be one of: auto, sqlite, web3")

    try:
        return Web3Client()
    except BackendUnavailableError:
        return SqliteClient()
