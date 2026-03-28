import pytest


from backend.plugin.api_testing.service.test_suite_service import normalize_suite_case_ids


def test_normalize_suite_case_ids_deduplicates_and_preserves_order() -> None:
    result = normalize_suite_case_ids([3, 1, 3, 2, 1, 4])

    assert result == [3, 1, 2, 4]


def test_normalize_suite_case_ids_ignores_non_positive_values() -> None:
    result = normalize_suite_case_ids([0, -1, 5, 0, 6])

    assert result == [5, 6]
