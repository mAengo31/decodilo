"""Provider metadata host discovery for Lambda SSH connectivity probes."""

from __future__ import annotations

import ipaddress
import json
import re
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

HostDiscoveryStatus = Literal["FOUND", "NOT_FOUND", "AMBIGUOUS", "INVALID"]

_HOST_KEYS = {
    "ip",
    "ip_address",
    "public_ip",
    "public_ip_address",
    "publicip",
    "publicipv4",
    "hostname",
    "host",
    "ssh_host",
    "sshhost",
    "ssh_hostname",
    "instance_ip",
    "external_ip",
    "externalip",
}
_DIAGNOSTIC_URL_KEYS = {"jupyter_url"}
_PRIVATE_KEYS = {"private_ip", "privateip", "private_ip_address"}
_DNS_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[A-Za-z0-9-]{1,63}\.)*[A-Za-z0-9][A-Za-z0-9-]{0,62}\.?"
    r"$"
)


class LambdaSSHHostDiscoveryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    status: HostDiscoveryStatus
    host: str | None = None
    host_redacted: str | None = None
    source_path: str | None = None
    source: str | None = None
    candidate_hosts: list[str] = Field(default_factory=list)
    rejected_candidates: list[dict[str, str]] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    sanitized_metadata_keys: list[str] = Field(default_factory=list)
    sanitized_metadata_key_paths: list[str] = Field(default_factory=list)
    poll_count: int = 0
    duration_seconds: float = 0.0
    override_used: bool = False
    private_ip_allowed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_result(self) -> LambdaSSHHostDiscoveryResult:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("host discovery cannot enable launch flags or billable action")
        if self.status == "FOUND" and not self.host:
            raise ValueError("FOUND host discovery requires host")
        if self.status != "FOUND" and self.host is not None:
            raise ValueError("non-FOUND host discovery cannot carry raw host")
        return self

    def public_copy(self) -> LambdaSSHHostDiscoveryResult:
        return self.model_copy(update={"host": None})

    def to_json(self, *, public: bool = True) -> str:
        report = self.public_copy() if public else self
        return json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def extract_ssh_host_from_instance_metadata(
    instance_metadata: dict[str, Any],
    *,
    allow_private_ip: bool = False,
    host_override: str | None = None,
    source: str | None = None,
) -> LambdaSSHHostDiscoveryResult:
    """Find an SSH host in provider metadata without trusting arbitrary strings."""

    keys, paths = _metadata_key_summary(instance_metadata)
    if host_override:
        validated = _validate_host_candidate(
            host_override,
            path="operator_override",
            allow_private_ip=allow_private_ip,
            key_name="operator_override",
        )
        if validated["accepted"]:
            host = str(validated["host"])
            return LambdaSSHHostDiscoveryResult(
                status="FOUND",
                host=host,
                host_redacted=_redact_host(host),
                source_path="operator_override",
                source="operator_override",
                candidate_hosts=[_redact_host(host)],
                reason_codes=["operator_override_used"],
                sanitized_metadata_keys=keys,
                sanitized_metadata_key_paths=paths,
                override_used=True,
                private_ip_allowed=allow_private_ip,
            )
        return LambdaSSHHostDiscoveryResult(
            status="INVALID",
            rejected_candidates=[
                _rejected("operator_override", host_override, validated["reason"])
            ],
            reason_codes=["operator_override_invalid", str(validated["reason"])],
            sanitized_metadata_keys=keys,
            sanitized_metadata_key_paths=paths,
            private_ip_allowed=allow_private_ip,
        )

    accepted: list[tuple[str, str]] = []
    rejected: list[dict[str, str]] = []
    for path, key_name, value in _iter_candidate_values(instance_metadata):
        validation = _validate_host_candidate(
            value,
            path=path,
            key_name=key_name,
            allow_private_ip=allow_private_ip,
        )
        if validation["accepted"]:
            accepted.append((path, str(validation["host"])))
        else:
            rejected.append(_rejected(path, value, str(validation["reason"])))

    unique_hosts: list[str] = []
    unique_paths: dict[str, str] = {}
    for path, host in accepted:
        if host not in unique_hosts:
            unique_hosts.append(host)
            unique_paths[host] = path
    if len(unique_hosts) == 1:
        host = unique_hosts[0]
        return LambdaSSHHostDiscoveryResult(
            status="FOUND",
            host=host,
            host_redacted=_redact_host(host),
            source_path=unique_paths[host],
            source=source,
            candidate_hosts=[_redact_host(host)],
            rejected_candidates=rejected,
            reason_codes=["host_found"],
            sanitized_metadata_keys=keys,
            sanitized_metadata_key_paths=paths,
            private_ip_allowed=allow_private_ip,
        )
    if len(unique_hosts) > 1:
        return LambdaSSHHostDiscoveryResult(
            status="AMBIGUOUS",
            source=source,
            candidate_hosts=[_redact_host(host) for host in unique_hosts],
            rejected_candidates=rejected,
            reason_codes=["multiple_distinct_host_candidates"],
            sanitized_metadata_keys=keys,
            sanitized_metadata_key_paths=paths,
            private_ip_allowed=allow_private_ip,
        )
    reason_codes = ["no_host_candidate_found"]
    if rejected:
        reason_codes.append("host_candidates_rejected")
    return LambdaSSHHostDiscoveryResult(
        status="NOT_FOUND",
        source=source,
        rejected_candidates=rejected,
        reason_codes=reason_codes,
        sanitized_metadata_keys=keys,
        sanitized_metadata_key_paths=paths,
        private_ip_allowed=allow_private_ip,
    )


def poll_ssh_host_from_provider_metadata(
    *,
    metadata_fetcher: Callable[[], Iterable[tuple[str, dict[str, Any]]]],
    timeout_seconds: float = 120.0,
    interval_seconds: float = 2.0,
    max_polls: int | None = None,
    allow_private_ip: bool = False,
    host_override: str | None = None,
    sleep_func: Callable[[float], None] = time.sleep,
) -> LambdaSSHHostDiscoveryResult:
    started = time.monotonic()
    poll_count = 0
    keys_seen: set[str] = set()
    paths_seen: set[str] = set()
    rejected: list[dict[str, str]] = []
    latest_reasons: list[str] = []
    while True:
        poll_count += 1
        if host_override:
            result = extract_ssh_host_from_instance_metadata(
                {},
                allow_private_ip=allow_private_ip,
                host_override=host_override,
                source="operator_override",
            )
            return _with_poll_metadata(result, poll_count, started)
        for source, payload in metadata_fetcher():
            result = extract_ssh_host_from_instance_metadata(
                payload,
                allow_private_ip=allow_private_ip,
                source=source,
            )
            keys_seen.update(result.sanitized_metadata_keys)
            paths_seen.update(result.sanitized_metadata_key_paths)
            rejected.extend(result.rejected_candidates)
            latest_reasons = result.reason_codes
            if result.status in {"FOUND", "AMBIGUOUS", "INVALID"}:
                return _with_poll_metadata(
                    result.model_copy(
                        update={
                            "sanitized_metadata_keys": sorted(keys_seen),
                            "sanitized_metadata_key_paths": sorted(paths_seen),
                            "rejected_candidates": _dedupe_rejections(rejected),
                        }
                    ),
                    poll_count,
                    started,
                )
        elapsed = time.monotonic() - started
        if (max_polls is not None and poll_count >= max_polls) or elapsed >= timeout_seconds:
            return LambdaSSHHostDiscoveryResult(
                status="NOT_FOUND",
                reason_codes=sorted(set([*latest_reasons, "host_discovery_timeout"])),
                rejected_candidates=_dedupe_rejections(rejected),
                sanitized_metadata_keys=sorted(keys_seen),
                sanitized_metadata_key_paths=sorted(paths_seen),
                poll_count=poll_count,
                duration_seconds=round(elapsed, 6),
                private_ip_allowed=allow_private_ip,
            )
        sleep_func(max(0.0, min(interval_seconds, timeout_seconds - elapsed)))


def _with_poll_metadata(
    result: LambdaSSHHostDiscoveryResult,
    poll_count: int,
    started: float,
) -> LambdaSSHHostDiscoveryResult:
    return result.model_copy(
        update={
            "poll_count": poll_count,
            "duration_seconds": round(time.monotonic() - started, 6),
        }
    )


def _iter_candidate_values(value: Any, path: str = "$") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path != "$" else str(key)
            normalized = _normalize_key(str(key))
            if (
                normalized in _HOST_KEYS
                or normalized in _PRIVATE_KEYS
                or normalized in _DIAGNOSTIC_URL_KEYS
            ):
                yield child, str(key), item
            yield from _iter_candidate_values(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_candidate_values(item, f"{path}[{index}]")


def _validate_host_candidate(
    value: Any,
    *,
    path: str,
    key_name: str,
    allow_private_ip: bool,
) -> dict[str, object]:
    if not isinstance(value, str) or not value.strip():
        return {"accepted": False, "reason": "empty_or_non_string_value"}
    raw = value.strip()
    parsed = urlparse(raw)
    if parsed.scheme:
        return {"accepted": False, "reason": "url_value_rejected"}
    if _normalize_key(key_name) in _DIAGNOSTIC_URL_KEYS:
        return {"accepted": False, "reason": "diagnostic_url_not_ssh_host"}
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError:
        ip = None
    if ip is not None:
        if ip.is_loopback or ip.is_unspecified or ip.is_multicast:
            return {"accepted": False, "reason": "non_routable_ip_rejected"}
        if (ip.is_private or not ip.is_global) and not allow_private_ip:
            return {"accepted": False, "reason": "private_or_non_global_ip_rejected"}
        return {"accepted": True, "host": raw}
    candidate = raw[:-1] if raw.endswith(".") else raw
    if not _DNS_RE.match(candidate) or "." not in candidate:
        return {"accepted": False, "reason": "invalid_hostname"}
    if any(part.startswith("-") or part.endswith("-") for part in candidate.split(".")):
        return {"accepted": False, "reason": "invalid_hostname"}
    return {"accepted": True, "host": candidate}


def _metadata_key_summary(value: Any, path: str = "$") -> tuple[list[str], list[str]]:
    keys: set[str] = set()
    paths: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path != "$" else str(key)
            keys.add(str(key))
            paths.add(child)
            child_keys, child_paths = _metadata_key_summary(item, child)
            keys.update(child_keys)
            paths.update(child_paths)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            child_keys, child_paths = _metadata_key_summary(item, f"{path}[{index}]")
            keys.update(child_keys)
            paths.update(child_paths)
    return sorted(keys), sorted(paths)


def _normalize_key(value: str) -> str:
    return value.replace("-", "_").replace(" ", "_").lower()


def _redact_host(host: str | None) -> str | None:
    if not host:
        return None
    if len(host) <= 8:
        return "<redacted-host>"
    return f"{host[:3]}...{host[-3:]}"


def _rejected(path: str, value: Any, reason: str) -> dict[str, str]:
    return {"path": path, "value_redacted": "<redacted>", "reason": reason}


def _dedupe_rejections(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for item in items:
        key = (item.get("path", ""), item.get("reason", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def write_lambda_ssh_host_discovery_result(
    path: str | Path,
    result: LambdaSSHHostDiscoveryResult,
    *,
    public: bool = True,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result.to_json(public=public), encoding="utf-8")
