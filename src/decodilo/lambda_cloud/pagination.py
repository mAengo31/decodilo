"""Small pagination helpers for Lambda read-only discovery fixtures."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LambdaPaginationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_pages: int = Field(default=10, gt=0)
    max_items: int = Field(default=1000, gt=0)


class LambdaPaginationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[Any] = Field(default_factory=list)
    pages_read: int
    pagination_observed: bool
    next_token: str | None = None
    warnings: list[str] = Field(default_factory=list)


class LambdaPaginationError(ValueError):
    """Raised when a fixture pagination pattern is malformed or unsafe."""


FetchPage = Callable[[str | None, int, int], Any]


def paginate_lambda_read(
    fetch_page: FetchPage,
    *,
    config: LambdaPaginationConfig | None = None,
) -> LambdaPaginationResult:
    config = config or LambdaPaginationConfig()
    items: list[Any] = []
    seen_tokens: set[str] = set()
    token: str | None = None
    pagination_observed = False
    warnings: list[str] = []
    for page_number in range(1, config.max_pages + 1):
        payload = fetch_page(token, page_number, len(items))
        page_items, next_token = extract_lambda_page(payload)
        items.extend(page_items)
        if len(items) > config.max_items:
            warnings.append("max_items reached; pagination result truncated")
            items = items[: config.max_items]
            return LambdaPaginationResult(
                items=items,
                pages_read=page_number,
                pagination_observed=True,
                next_token=next_token,
                warnings=warnings,
            )
        if next_token is None:
            return LambdaPaginationResult(
                items=items,
                pages_read=page_number,
                pagination_observed=pagination_observed,
                warnings=warnings,
            )
        pagination_observed = True
        if next_token in seen_tokens:
            raise LambdaPaginationError("pagination token loop detected")
        seen_tokens.add(next_token)
        token = next_token
    raise LambdaPaginationError("max_pages reached before pagination completed")


def extract_lambda_page(payload: Any) -> tuple[list[Any], str | None]:
    if isinstance(payload, list):
        return payload, None
    if not isinstance(payload, dict):
        raise LambdaPaginationError("Lambda paginated payload must be a list or object")
    items = payload.get("data", payload.get("items", payload.get("results", [])))
    if not isinstance(items, list):
        raise LambdaPaginationError("Lambda paginated payload items must be a list")
    token = payload.get("next_token")
    if token is None:
        token = payload.get("next")
    if token is None and payload.get("page") is not None:
        token = _offset_next_token(payload)
    if token is not None and not isinstance(token, str):
        raise LambdaPaginationError("Lambda pagination token must be a string")
    return items, token or None


def _offset_next_token(payload: dict[str, Any]) -> str | None:
    page = payload.get("page")
    total_pages = payload.get("total_pages")
    if not isinstance(page, int):
        raise LambdaPaginationError("page pagination requires integer page")
    if total_pages is not None and not isinstance(total_pages, int):
        raise LambdaPaginationError("total_pages must be an integer")
    if total_pages is not None and page >= total_pages:
        return None
    return f"page:{page + 1}"
