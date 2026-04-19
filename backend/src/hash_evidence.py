"""SHA-256 fingerprinting for digital evidence files."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from .config import CHUNK_SIZE, DEFAULT_EVIDENCE_PATH


def sha256_file(path: Path | str) -> str:
    """Return the SHA-256 hex digest for a file, streaming in fixed chunks."""
    file_path = Path(path)
    digest = hashlib.sha256()

    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a SHA-256 hash for an evidence file.")
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        default=DEFAULT_EVIDENCE_PATH,
        help="Path to the evidence file; defaults to ./evidence",
    )
    args = parser.parse_args(argv)

    print(sha256_file(args.file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
