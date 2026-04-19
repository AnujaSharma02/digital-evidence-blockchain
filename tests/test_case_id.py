from unittest.mock import patch

import pytest

from src.case_id import CaseIdGenerationError, generate_case_id, sanitize_case_name


class Lookup:
    def __init__(self, existing: set[str] | None = None) -> None:
        self.existing = existing or set()

    def exists(self, case_id: str) -> bool:
        return case_id in self.existing


def test_sanitize_case_name() -> None:
    assert sanitize_case_name("Cyber Fraud Case") == "cyber-fraud-case"
    assert sanitize_case_name("CASE 2026!!") == "case-2026"
    assert sanitize_case_name("!!!") == "case"


def test_generate_case_id_appends_uppercase_key() -> None:
    with patch("src.case_id.random_key", return_value="A3F8B21C"):
        assert generate_case_id("Cyber Fraud Case", Lookup()) == "cyber-fraud-case-A3F8B21C"


def test_generate_case_id_truncates_slug_to_40_chars() -> None:
    with patch("src.case_id.random_key", return_value="F92D4AB1"):
        case_id = generate_case_id("A" * 80, Lookup())

    slug, key = case_id.rsplit("-", 1)
    assert len(slug) == 40
    assert key == "F92D4AB1"


def test_generate_case_id_retries_on_collision() -> None:
    keys = iter(["AAAAAAAA", "BBBBBBBB"])
    lookup = Lookup({"email-evidence-AAAAAAAA"})

    with patch("src.case_id.random_key", side_effect=lambda: next(keys)):
        assert generate_case_id("email evidence", lookup) == "email-evidence-BBBBBBBB"


def test_generate_case_id_errors_after_repeated_collisions() -> None:
    with patch("src.case_id.random_key", return_value="AAAAAAAA"):
        with pytest.raises(CaseIdGenerationError):
            generate_case_id("email evidence", Lookup({"email-evidence-AAAAAAAA"}))

