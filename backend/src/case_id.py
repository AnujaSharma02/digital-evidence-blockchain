"""Case ID generation for API-registered evidence."""

from __future__ import annotations

import re
import secrets
import string
from typing import Protocol


MAX_SLUG_LENGTH = 40
RANDOM_KEY_LENGTH = 8
MAX_COLLISION_RETRIES = 5
KEY_ALPHABET = string.ascii_uppercase + string.digits


class CaseLookup(Protocol):
    def exists(self, case_id: str) -> bool:
        ...


class CaseIdGenerationError(RuntimeError):
    """Raised when a unique case ID cannot be generated."""


def sanitize_case_name(case_name: str) -> str:
    slug = case_name.strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    slug = slug[:MAX_SLUG_LENGTH].strip("-")
    return slug or "case"


def random_key() -> str:
    return "".join(secrets.choice(KEY_ALPHABET) for _ in range(RANDOM_KEY_LENGTH))


def generate_case_id(case_name: str, lookup: CaseLookup) -> str:
    slug = sanitize_case_name(case_name)
    for _ in range(MAX_COLLISION_RETRIES):
        candidate = f"{slug}-{random_key()}"
        if not lookup.exists(candidate):
            return candidate
    raise CaseIdGenerationError("Could not generate a unique case ID after 5 attempts")

