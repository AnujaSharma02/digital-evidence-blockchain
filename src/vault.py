"""Off-chain local evidence vault helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from .config import VAULT_ROOT


INVALID_CASE_CHARS = set('<>:"/\\|?*')


def validate_case_id(case_id: str) -> str:
    cleaned = case_id.strip()
    if not cleaned:
        raise ValueError("case_id must not be empty")
    if cleaned in {".", ".."} or any(ch in INVALID_CASE_CHARS for ch in cleaned):
        raise ValueError("case_id contains unsafe path characters")
    return cleaned


def case_dir(case_id: str, vault_root: Path | str = VAULT_ROOT) -> Path:
    return Path(vault_root) / validate_case_id(case_id)


def store_file(case_id: str, src_path: Path | str, vault_root: Path | str = VAULT_ROOT) -> Path:
    """Copy an evidence file into the local off-chain vault and return its path."""
    source = Path(src_path)
    if not source.is_file():
        raise FileNotFoundError(f"Evidence file not found: {source}")

    target_dir = case_dir(case_id, vault_root)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    shutil.copy2(source, target)
    return target


def get_case_files(case_id: str, vault_root: Path | str = VAULT_ROOT) -> list[Path]:
    directory = case_dir(case_id, vault_root)
    if not directory.exists():
        return []
    return sorted(path for path in directory.iterdir() if path.is_file())


def get_vaulted_file(
    case_id: str,
    filename: str | None = None,
    vault_root: Path | str = VAULT_ROOT,
) -> Path:
    files = get_case_files(case_id, vault_root)
    if filename is not None:
        target = case_dir(case_id, vault_root) / Path(filename).name
        if target.is_file():
            return target
        raise FileNotFoundError(f"No vaulted file named {filename!r} for case {case_id}")

    if not files:
        raise FileNotFoundError(f"No vaulted evidence found for case {case_id}")
    if len(files) > 1:
        raise ValueError("Multiple vaulted files found; pass filename explicitly")
    return files[0]


def read_file(case_id: str, filename: str | None = None, vault_root: Path | str = VAULT_ROOT) -> bytes:
    """Read a vaulted evidence file.

    TODO: Replace local plaintext storage with AES-GCM encryption for a production system.
    """
    return get_vaulted_file(case_id, filename, vault_root).read_bytes()

