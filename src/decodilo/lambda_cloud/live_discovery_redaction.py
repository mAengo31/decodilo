"""Redaction utilities for Lambda live discovery artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

LambdaRedactionMode = Literal["public_summary", "local_private_report"]

_SECRET_RE = re.compile(
    r"(Bearer\s+[A-Za-z0-9._~+/=-]+|"
    r"lambda[_-]?[A-Za-z0-9._~+/=-]{16,}|"
    r"AKIA[0-9A-Z]{12,}|"
    r"(api[_-]?key|authorization|token|secret|password|private[_-]?key)"
    r"\s*[:=]\s*[A-Za-z0-9._~+/=-]{8,})",
    re.IGNORECASE,
)
_SENSITIVE_ID_KEYS = {
    "instance_id",
    "filesystem_id",
    "ssh_key_id",
    "key_id",
    "public_key",
    "private_key",
    "authorization",
}


class LambdaLiveDiscoveryRedactionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: LambdaRedactionMode = "local_private_report"
    redact_instance_ids_in_public_summary: bool = True
    redact_filesystem_ids_in_public_summary: bool = True
    redact_private_ips_in_public_summary: bool = True


class LambdaRedactionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    mode: LambdaRedactionMode
    redactions_applied: int = 0
    secret_leaks: list[str] = Field(default_factory=list)


def redact_lambda_payload(
    payload: Any,
    *,
    policy: LambdaLiveDiscoveryRedactionPolicy | None = None,
) -> Any:
    policy = policy or LambdaLiveDiscoveryRedactionPolicy()
    return _redact(payload, policy=policy, key=None)


def redact_lambda_text(value: str) -> str:
    return _SECRET_RE.sub("<redacted-secret>", value)


def scan_lambda_secret_leaks(payload: Any) -> list[str]:
    serialized = json.dumps(_plain(payload), sort_keys=True, default=str)
    if not _SECRET_RE.search(serialized):
        return []
    return ["secret-like value detected in Lambda discovery artifact"]


def audit_lambda_redaction(
    payload: Any,
    *,
    policy: LambdaLiveDiscoveryRedactionPolicy | None = None,
) -> LambdaRedactionReport:
    policy = policy or LambdaLiveDiscoveryRedactionPolicy()
    leaks = scan_lambda_secret_leaks(payload)
    redacted = redact_lambda_payload(payload, policy=policy)
    return LambdaRedactionReport(
        passed=not leaks and not scan_lambda_secret_leaks(redacted),
        mode=policy.mode,
        redactions_applied=_count_changed(_plain(payload), redacted),
        secret_leaks=leaks,
    )


def redact_lambda_identifier(value: str, *, keep_prefix: int = 4) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    prefix = value[:keep_prefix] if keep_prefix > 0 else ""
    return f"{prefix}<redacted:{digest}>"


def _redact(
    value: Any,
    *,
    policy: LambdaLiveDiscoveryRedactionPolicy,
    key: str | None,
) -> Any:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        return {
            str(item_key): _redact(
                item_value,
                policy=policy,
                key=str(item_key),
            )
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_redact(item, policy=policy, key=key) for item in value]
    if isinstance(value, str):
        if _is_secret_key(key):
            return "<redacted-secret>"
        cleaned = redact_lambda_text(value)
        if policy.mode == "public_summary" and _is_public_sensitive_key(key):
            return redact_lambda_identifier(cleaned)
        return cleaned
    return value


def _is_secret_key(key: str | None) -> bool:
    if key is None:
        return False
    lowered = key.lower()
    secret_terms = (
        "authorization",
        "api_key",
        "token",
        "secret",
        "password",
        "private_key",
    )
    return any(term in lowered for term in secret_terms)


def _is_public_sensitive_key(key: str | None) -> bool:
    if key is None:
        return False
    lowered = key.lower()
    return lowered in _SENSITIVE_ID_KEYS or lowered.endswith("_id")


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _count_changed(before: Any, after: Any) -> int:
    if type(before) is not type(after):
        return 1
    if isinstance(before, dict) and isinstance(after, dict):
        return sum(
            _count_changed(before.get(key), after.get(key))
            for key in set(before) | set(after)
        )
    if isinstance(before, list) and isinstance(after, list):
        return sum(_count_changed(left, right) for left, right in zip(before, after, strict=False))
    return int(before != after)
