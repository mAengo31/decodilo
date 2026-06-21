"""Response-shape summaries for Lambda read-only discovery calibration."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LambdaResponseShapeSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    top_level_type: str
    item_count: int | None = None
    field_names: list[str] = Field(default_factory=list)
    item_field_names: list[str] = Field(default_factory=list)
    unknown_fields_seen: list[str] = Field(default_factory=list)
    pagination_observed: bool = False

    @property
    def compact(self) -> str:
        parts = [self.top_level_type]
        if self.item_count is not None:
            parts.append(f"items={self.item_count}")
        if self.field_names:
            parts.append("fields=" + ",".join(self.field_names))
        if self.item_field_names:
            parts.append("item_fields=" + ",".join(self.item_field_names))
        if self.unknown_fields_seen:
            parts.append("unknown=" + ",".join(self.unknown_fields_seen))
        if self.pagination_observed:
            parts.append("pagination=true")
        return "; ".join(parts)


def summarize_lambda_response_shape(payload: Any) -> LambdaResponseShapeSummary:
    normalized = _to_plain(payload)
    if isinstance(normalized, list):
        item_fields = _collect_dict_keys(normalized)
        unknown = _collect_unknown_fields(payload)
        return LambdaResponseShapeSummary(
            top_level_type="list",
            item_count=len(normalized),
            item_field_names=item_fields,
            unknown_fields_seen=unknown,
        )
    if isinstance(normalized, dict):
        items = _extract_items(normalized)
        return LambdaResponseShapeSummary(
            top_level_type="dict",
            item_count=None if items is None else len(items),
            field_names=sorted(str(key) for key in normalized),
            item_field_names=_collect_dict_keys(items or []),
            unknown_fields_seen=_collect_unknown_fields(payload),
            pagination_observed=_has_pagination_marker(normalized),
        )
    return LambdaResponseShapeSummary(top_level_type=type(normalized).__name__)


def collect_lambda_unknown_fields(payload: Any) -> list[str]:
    return _collect_unknown_fields(payload)


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, tuple):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_plain(item) for key, item in value.items()}
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


def _extract_items(payload: dict[str, Any]) -> list[Any] | None:
    for key in ("data", "items", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return None


def _collect_dict_keys(items: Iterable[Any]) -> list[str]:
    keys: set[str] = set()
    for item in items:
        plain = _to_plain(item)
        if isinstance(plain, dict):
            keys.update(str(key) for key in plain)
    return sorted(keys)


def _collect_unknown_fields(payload: Any) -> list[str]:
    unknown: set[str] = set()
    if hasattr(payload, "metadata"):
        metadata = payload.metadata
        if isinstance(metadata, dict):
            unknown.update(str(key) for key in metadata)
    if isinstance(payload, list | tuple):
        for item in payload:
            unknown.update(_collect_unknown_fields(item))
    if isinstance(payload, dict):
        metadata = payload.get("metadata")
        if isinstance(metadata, dict):
            unknown.update(str(key) for key in metadata)
        for item in payload.values():
            unknown.update(_collect_unknown_fields(item))
    return sorted(unknown)


def _has_pagination_marker(payload: dict[str, Any]) -> bool:
    return any(
        key in payload and payload.get(key) not in (None, "", [], {})
        for key in ("next_token", "next", "page", "limit", "offset")
    )
