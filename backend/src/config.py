"""Project-wide configuration for the evidence integrity prototype."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional until requirements are installed
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_PATH = Path(os.getenv("EVIDENCE_FILE", PROJECT_ROOT / "evidence"))
SAMPLE_EVIDENCE_PATH = PROJECT_ROOT / "samples" / "email.eml"
VAULT_ROOT = Path(os.getenv("EVIDENCE_VAULT", PROJECT_ROOT / "evidence_vault"))
DATA_DIR = Path(os.getenv("EVIDENCE_DATA_DIR", PROJECT_ROOT / "data"))
SQLITE_PATH = Path(os.getenv("EVIDENCE_SQLITE_PATH", DATA_DIR / "ledger.sqlite"))

GANACHE_URL = os.getenv("GANACHE_URL", "http://127.0.0.1:7545")
CONTRACT_ADDRESS = os.getenv("EVIDENCE_CONTRACT_ADDRESS", "")
BACKEND = os.getenv("EVIDENCE_BACKEND", "auto").lower()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "")

CHUNK_SIZE = 64 * 1024
