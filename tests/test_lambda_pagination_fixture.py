import pytest

from decodilo.lambda_cloud.pagination import (
    LambdaPaginationConfig,
    LambdaPaginationError,
    paginate_lambda_read,
)


def test_lambda_pagination_accepts_non_paginated_response() -> None:
    result = paginate_lambda_read(lambda token, page, count: [{"id": "one"}])

    assert result.items == [{"id": "one"}]
    assert result.pages_read == 1
    assert result.pagination_observed is False


def test_lambda_pagination_next_token_fixture() -> None:
    pages = {
        None: {"items": [{"id": "one"}], "next_token": "two"},
        "two": {"items": [{"id": "two"}]},
    }
    result = paginate_lambda_read(lambda token, page, count: pages[token])

    assert [item["id"] for item in result.items] == ["one", "two"]
    assert result.pagination_observed is True


def test_lambda_pagination_rejects_token_loop_and_max_pages() -> None:
    with pytest.raises(LambdaPaginationError, match="token loop"):
        paginate_lambda_read(lambda token, page, count: {"items": [], "next_token": "same"})

    with pytest.raises(LambdaPaginationError, match="max_pages"):
        paginate_lambda_read(
            lambda token, page, count: {"items": [], "next_token": str(page)},
            config=LambdaPaginationConfig(max_pages=2, max_items=10),
        )


def test_lambda_pagination_rejects_malformed_payload() -> None:
    with pytest.raises(LambdaPaginationError):
        paginate_lambda_read(lambda token, page, count: {"items": "not-a-list"})
