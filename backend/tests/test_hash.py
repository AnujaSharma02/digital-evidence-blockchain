from pathlib import Path
from uuid import uuid4

from src.hash_evidence import sha256_file


def workspace(name: str) -> Path:
    path = Path("test_runs") / name / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_sha256_file_is_deterministic() -> None:
    evidence = workspace("hash") / "evidence.bin"
    evidence.write_bytes(b"chain of custody")

    assert sha256_file(evidence) == sha256_file(evidence)


def test_sha256_file_changes_after_one_byte_change() -> None:
    evidence = workspace("hash") / "evidence.bin"
    evidence.write_bytes(b"chain of custody")
    before = sha256_file(evidence)

    evidence.write_bytes(b"chain of custody.")

    assert sha256_file(evidence) != before
