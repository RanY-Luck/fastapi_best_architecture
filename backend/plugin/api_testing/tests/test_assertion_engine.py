from backend.plugin.api_testing.utils.assertion import (
    Assertion,
    AssertionEngine,
    AssertionSource,
    AssertionType,
)


def test_is_empty_does_not_treat_zero_as_empty() -> None:
    result = AssertionEngine.execute_assertion(
        Assertion(source=AssertionSource.JSON, type=AssertionType.IS_EMPTY, path="$.count"),
        {"json": {"count": 0}},
    )

    assert result.success is False
    assert result.actual == 0


def test_header_assertion_supports_plain_header_name_path() -> None:
    result = AssertionEngine.execute_assertion(
        Assertion(
            source=AssertionSource.HEADERS,
            type=AssertionType.CONTAINS,
            path="Content-Type",
            expected="application/json",
        ),
        {"headers": {"Content-Type": "application/json; charset=utf-8"}},
    )

    assert result.success is True
    assert result.actual == "application/json; charset=utf-8"


def test_elapsed_time_can_be_asserted_from_top_level_response_data() -> None:
    result = AssertionEngine.execute_assertion(
        Assertion(
            source=AssertionSource.JSON,
            type=AssertionType.LESS_THAN,
            path="$.elapsed_time",
            expected=1000,
        ),
        {"json": {"data": {}}, "elapsed_time": 120},
    )

    assert result.success is True
    assert result.actual == 120
