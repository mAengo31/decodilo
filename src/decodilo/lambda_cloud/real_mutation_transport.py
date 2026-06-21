"""Guarded M029 Lambda mutation transport.

This module is intentionally narrow: the only mutating operation paths are
Lambda's documented first-launch POST and owned-termination POST endpoints.
Tests exercise this transport with the in-memory fake server only.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.endpoint_policy import (
    LambdaEndpoint,
    LambdaEndpointPolicy,
    endpoint_for_operation,
    m029_endpoint_for_operation,
)
from decodilo.lambda_cloud.fake_server_failure_modes import (
    LambdaMinimalFakeFailure,
    LambdaMinimalFakeFailureMode,
)
from decodilo.lambda_cloud.fake_server_resource_registry import (
    LambdaFakeServerResourceRegistry,
)
from decodilo.lambda_cloud.http_response_capture import capture_lambda_http_response
from decodilo.lambda_cloud.mutation_guard import LambdaMutationGuard
from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnostics,
)
from decodilo.lambda_cloud.real_launch_arming import LambdaM029ArmingToken


class LambdaRealMutationTransportError(RuntimeError):
    """Sanitized M029 transport error."""


class LambdaM029TransportConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: str = "https://cloud.lambdalabs.com/api/v1"
    timeout_seconds: float = Field(default=30.0, gt=0)
    fake_server_mode: bool = False
    allow_real_lambda_api: bool = False
    user_agent: str = "decodilo-lambda-m029-first-launch/0.1"

    @model_validator(mode="after")
    def _mode_consistent(self) -> LambdaM029TransportConfig:
        if self.fake_server_mode:
            if not _is_local_or_memory_url(self.base_url):
                raise ValueError("M029 fake-server mode requires localhost or memory URL")
        elif not self.allow_real_lambda_api:
            raise ValueError("M029 real transport requires explicit real API allowance")
        return self


class LambdaM029TransportAuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation: str
    method: str
    endpoint: str
    request_state: Literal[
        "request_not_sent",
        "request_sent",
        "response_received",
        "response_lost_or_timeout",
    ]
    status_code: int | None = None
    idempotency_key_present: bool
    arming_token_present: bool
    authorization_header_redacted: bool = True
    request_body_redacted: dict[str, Any] = Field(default_factory=dict)
    real_lambda_api_used: bool = False
    billable_action_performed: bool = False


@dataclass(frozen=True)
class LambdaM029HTTPResponse:
    status_code: int
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)
    reason: str | None = None


M029HTTPCaller = Callable[[Request, bytes, float], LambdaM029HTTPResponse]


@dataclass
class LambdaM029RealMutationTransport:
    config: LambdaM029TransportConfig
    api_key: str | None = None
    endpoint_policy: LambdaEndpointPolicy = field(
        default_factory=lambda: LambdaEndpointPolicy(
            mode="m029_first_launch",
            allow_non_get=True,
        )
    )
    mutation_guard: LambdaMutationGuard = field(default_factory=LambdaMutationGuard)
    fake_registry: LambdaFakeServerResourceRegistry = field(
        default_factory=LambdaFakeServerResourceRegistry
    )
    http_caller: M029HTTPCaller | None = None
    audit_log: list[LambdaM029TransportAuditEvent] = field(default_factory=list)
    diagnostics_log: list[LambdaMutationTransportDiagnostics] = field(default_factory=list)

    def request_json(
        self,
        *,
        operation: str,
        payload: dict[str, Any] | None = None,
        arming_token: LambdaM029ArmingToken,
        idempotency_key: str,
        instance_id: str | None = None,
        failure_mode: LambdaMinimalFakeFailureMode = "none",
    ) -> dict[str, Any]:
        self._authorize(operation, arming_token=arming_token, idempotency_key=idempotency_key)
        if operation in {"list_instances", "get_instance"}:
            endpoint = endpoint_for_operation(operation, instance_id=instance_id)
        else:
            endpoint = m029_endpoint_for_operation(operation)
        self._authorize_endpoint(endpoint, arming_token=arming_token)
        if self.config.fake_server_mode:
            return self._fake_request(
                operation=operation,
                payload=payload or {},
                endpoint=endpoint,
                idempotency_key=idempotency_key,
                failure_mode=failure_mode,
            )
        return self._real_request(
            operation=operation,
            payload=payload or {},
            endpoint=endpoint,
            arming_token=arming_token,
            idempotency_key=idempotency_key,
        )

    def _authorize(
        self,
        operation: str,
        *,
        arming_token: LambdaM029ArmingToken,
        idempotency_key: str,
    ) -> None:
        if not idempotency_key:
            raise LambdaRealMutationTransportError("M029 request requires idempotency key")
        arming_token.require_unused()
        allowed_operations = {
            "launch_one_instance",
            "terminate_owned_instance",
            "list_instances",
            "get_instance",
        }
        if operation not in allowed_operations:
            raise LambdaRealMutationTransportError("M029 transport denied unknown operation")
        if not self.config.fake_server_mode:
            if not self.api_key:
                raise LambdaRealMutationTransportError(
                    "M029 real request requires explicit key source"
                )
            if not arming_token.real_lambda_api_allowed:
                raise LambdaRealMutationTransportError(
                    "M029 arming token does not allow real Lambda API"
                )

    def _authorize_endpoint(
        self,
        endpoint: LambdaEndpoint,
        *,
        arming_token: LambdaM029ArmingToken,
    ) -> None:
        guard = self.mutation_guard.check_m029(
            endpoint.operation,
            armed=arming_token.arming_succeeded,
        )
        if not guard.allowed:
            raise LambdaRealMutationTransportError(guard.reason)
        if endpoint.method.upper() == "GET":
            policy = LambdaEndpointPolicy().check(endpoint)
        else:
            policy = self.endpoint_policy.check(endpoint)
        if not policy.allowed:
            raise LambdaRealMutationTransportError(policy.reason)

    def _fake_request(
        self,
        *,
        operation: str,
        payload: dict[str, Any],
        endpoint: LambdaEndpoint,
        idempotency_key: str,
        failure_mode: LambdaMinimalFakeFailureMode,
    ) -> dict[str, Any]:
        self._record(endpoint, "request_sent", idempotency_key, payload)
        try:
            if operation == "launch_one_instance":
                resource = self.fake_registry.launch(
                    instance_type=str(payload["instance_type_name"]),
                    region=str(payload["region_name"]),
                    idempotency_key=idempotency_key,
                )
                if failure_mode in {"launch_response_lost", "launch_timeout_but_created"}:
                    raise TimeoutError("fake launch response unavailable")
                if failure_mode == "malformed_launch_response":
                    return {"data": {"instance_ids": ["malformed-live-id"]}}
                response = {"data": {"instance_ids": [resource.instance_id]}}
            elif operation == "terminate_owned_instance":
                instance_ids = list(payload.get("instance_ids") or [])
                if len(instance_ids) != 1:
                    raise LambdaRealMutationTransportError(
                        "M029 terminate requires exactly one instance"
                    )
                resource = self.fake_registry.terminate(
                    instance_id=str(instance_ids[0]),
                    idempotency_key=idempotency_key,
                )
                if failure_mode in {
                    "terminate_response_lost",
                    "terminate_timeout_but_terminated",
                }:
                    raise TimeoutError("fake terminate response unavailable")
                if failure_mode == "malformed_terminate_response":
                    return {"data": {"terminated_instances": [{"id": "live-id"}]}}
                response = {
                    "data": {
                        "terminated_instances": [
                            {
                                "id": resource.instance_id,
                                "status": resource.lifecycle_state,
                            }
                        ]
                    }
                }
            elif operation == "list_instances":
                response = {
                    "data": [
                        {
                            "id": item.instance_id,
                            "status": item.lifecycle_state,
                            "hostname": f"{item.instance_id}.lambda.test",
                            "instance_type": {"name": item.instance_type},
                            "region": {"name": item.region},
                        }
                        for item in self.fake_registry.list_resources()
                        if item.lifecycle_state != "terminated"
                    ]
                }
            elif operation == "get_instance":
                resource = self.fake_registry.get(str(payload.get("instance_id") or ""))
                response = (
                    {
                        "data": {
                            "id": resource.instance_id,
                            "status": resource.lifecycle_state,
                            "network": {
                                "interfaces": [
                                    {"public_ip": f"{resource.instance_id}.lambda.test"}
                                ]
                            },
                        }
                    }
                    if resource
                    else {"error": {"code": "not_found"}}
                )
            else:  # pragma: no cover - guarded above
                raise LambdaRealMutationTransportError("unsupported operation")
        except (TimeoutError, LambdaMinimalFakeFailure) as exc:
            capture = capture_lambda_http_response(
                method=endpoint.method,
                endpoint_path_template=endpoint.path,
                endpoint_path=endpoint.path,
                mutation_operation_name=operation,
                exception=exc,
                billable_action_performed=False,
            )
            self.diagnostics_log.append(
                LambdaMutationTransportDiagnostics(
                    operation=operation,
                    stages=[
                        "before_request_constructed",
                        "request_constructed",
                        "request_sent",
                        "timeout_detected",
                        "exception_raised",
                    ],
                    response_capture=capture,
                    real_lambda_api_used=False,
                )
            )
            self._record(endpoint, "response_lost_or_timeout", idempotency_key, payload)
            raise TimeoutError("M029 fake response lost or timed out") from exc
        response_body = json.dumps(response, sort_keys=True).encode("utf-8")
        capture = capture_lambda_http_response(
            method=endpoint.method,
            endpoint_path_template=endpoint.path,
            endpoint_path=endpoint.path,
            mutation_operation_name=operation,
            status_code=200,
            headers={
                "content-type": "application/json",
                "content-length": str(len(response_body)),
            },
            body=response_body,
            billable_action_performed=False,
        )
        self.diagnostics_log.append(
            LambdaMutationTransportDiagnostics(
                operation=operation,
                stages=[
                    "before_request_constructed",
                    "request_constructed",
                    "request_sent",
                    "status_received",
                    "parse_started",
                    "parse_completed",
                ],
                response_capture=capture,
                real_lambda_api_used=False,
            )
        )
        self._record(endpoint, "response_received", idempotency_key, payload, status_code=200)
        return response

    def _real_request(
        self,
        *,
        operation: str,
        payload: dict[str, Any],
        endpoint: LambdaEndpoint,
        arming_token: LambdaM029ArmingToken,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if _is_real_url_forbidden(self.config.base_url, arming_token):
            raise LambdaRealMutationTransportError("M029 real Lambda URL blocked by arming")
        if not self.api_key:
            raise LambdaRealMutationTransportError("M029 real request missing explicit key source")
        body = json.dumps(payload).encode("utf-8")
        url = urljoin(self.config.base_url.rstrip("/") + "/", endpoint.path.lstrip("/"))
        request = Request(
            url,
            data=body if endpoint.method.upper() != "GET" else None,
            method=endpoint.method.upper(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": self.config.user_agent,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
        )
        self._record(
            endpoint,
            "request_sent",
            idempotency_key,
            payload,
            real_lambda_api_used=True,
            billable_action_performed=operation == "launch_one_instance",
        )
        request_started = time.monotonic()
        try:
            caller = self.http_caller or _default_http_caller
            response = caller(request, body, self.config.timeout_seconds)
        except (TimeoutError, URLError, HTTPError) as exc:
            status_code = int(exc.code) if isinstance(exc, HTTPError) else None
            response_body = exc.read() if isinstance(exc, HTTPError) else None
            headers = (
                {str(key): str(value) for key, value in exc.headers.items()}
                if isinstance(exc, HTTPError) and exc.headers is not None
                else None
            )
            capture = capture_lambda_http_response(
                method=endpoint.method,
                endpoint_path_template=endpoint.path,
                endpoint_path=endpoint.path,
                mutation_operation_name=operation,
                status_code=status_code,
                reason=getattr(exc, "reason", None),
                headers=headers,
                body=response_body,
                elapsed_seconds=time.monotonic() - request_started,
                exception=exc,
                billable_action_performed=operation == "launch_one_instance",
            )
            self.diagnostics_log.append(
                LambdaMutationTransportDiagnostics(
                    operation=operation,
                    stages=[
                        "before_request_constructed",
                        "request_constructed",
                        "request_sent",
                        *([] if status_code is None else ["status_received"]),
                        *(["timeout_detected"] if status_code is None else []),
                        "exception_raised",
                    ],
                    response_capture=capture,
                    real_lambda_api_used=True,
                )
            )
            self._record(endpoint, "response_lost_or_timeout", idempotency_key, payload)
            if status_code is not None:
                raise LambdaRealMutationTransportError("M029 real Lambda HTTP error") from exc
            raise TimeoutError("M029 real Lambda response lost or timed out") from exc
        capture = capture_lambda_http_response(
            method=endpoint.method,
            endpoint_path_template=endpoint.path,
            endpoint_path=endpoint.path,
            mutation_operation_name=operation,
            status_code=response.status_code,
            reason=response.reason,
            headers=response.headers,
            body=response.body,
            elapsed_seconds=time.monotonic() - request_started,
            billable_action_performed=operation == "launch_one_instance",
        )
        if response.status_code >= 400:
            self.diagnostics_log.append(
                LambdaMutationTransportDiagnostics(
                    operation=operation,
                    stages=[
                        "before_request_constructed",
                        "request_constructed",
                        "request_sent",
                        "status_received",
                        "exception_raised",
                    ],
                    response_capture=capture,
                    real_lambda_api_used=True,
                )
            )
            self._record(
                endpoint,
                "response_received",
                idempotency_key,
                payload,
                status_code=response.status_code,
                real_lambda_api_used=True,
                billable_action_performed=operation == "launch_one_instance",
            )
            raise LambdaRealMutationTransportError("M029 real Lambda HTTP error")
        if not response.body:
            self.diagnostics_log.append(
                LambdaMutationTransportDiagnostics(
                    operation=operation,
                    stages=[
                        "before_request_constructed",
                        "request_constructed",
                        "request_sent",
                        "status_received",
                        "parse_started",
                        "parse_completed",
                    ],
                    response_capture=capture,
                    real_lambda_api_used=True,
                )
            )
            self._record(
                endpoint,
                "response_received",
                idempotency_key,
                payload,
                status_code=response.status_code,
                real_lambda_api_used=True,
                billable_action_performed=operation == "launch_one_instance",
            )
            if operation == "terminate_owned_instance":
                return {}
            raise LambdaRealMutationTransportError("M029 response body was empty")
        try:
            decoded = json.loads(response.body.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            self.diagnostics_log.append(
                LambdaMutationTransportDiagnostics(
                    operation=operation,
                    stages=[
                        "before_request_constructed",
                        "request_constructed",
                        "request_sent",
                        "status_received",
                        "parse_started",
                        "parse_failed",
                        "exception_raised",
                    ],
                    response_capture=capture,
                    real_lambda_api_used=True,
                )
            )
            raise LambdaRealMutationTransportError("M029 response was malformed JSON") from exc
        self.diagnostics_log.append(
            LambdaMutationTransportDiagnostics(
                operation=operation,
                stages=[
                    "before_request_constructed",
                    "request_constructed",
                    "request_sent",
                    "status_received",
                    "parse_started",
                    "parse_completed",
                ],
                response_capture=capture,
                real_lambda_api_used=True,
            )
        )
        self._record(
            endpoint,
            "response_received",
            idempotency_key,
            payload,
            status_code=response.status_code,
            real_lambda_api_used=True,
            billable_action_performed=operation == "launch_one_instance",
        )
        return decoded

    def _record(
        self,
        endpoint: LambdaEndpoint,
        state: str,
        idempotency_key: str,
        payload: dict[str, Any],
        *,
        status_code: int | None = None,
        real_lambda_api_used: bool = False,
        billable_action_performed: bool = False,
    ) -> None:
        self.audit_log.append(
            LambdaM029TransportAuditEvent(
                operation=endpoint.operation,
                method=endpoint.method,
                endpoint=endpoint.path,
                request_state=state,  # type: ignore[arg-type]
                status_code=status_code,
                idempotency_key_present=bool(idempotency_key),
                arming_token_present=True,
                request_body_redacted=_redact_payload(payload),
                real_lambda_api_used=real_lambda_api_used,
                billable_action_performed=billable_action_performed,
            )
        )


def _default_http_caller(
    request: Request,
    body: bytes,
    timeout_seconds: float,
) -> LambdaM029HTTPResponse:
    del body
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - guarded
            return LambdaM029HTTPResponse(
                status_code=int(response.status),
                body=response.read(),
                headers={str(key): str(value) for key, value in response.headers.items()},
                reason=getattr(response, "reason", None),
            )
    except HTTPError as exc:
        return LambdaM029HTTPResponse(
            status_code=int(exc.code),
            body=exc.read(),
            headers={str(key): str(value) for key, value in exc.headers.items()},
            reason=str(exc.reason),
        )


def _redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(payload)
    for key in ["ssh_key_names", "file_system_names", "file_system_mounts"]:
        if key in redacted:
            redacted[key] = "<redacted>" if redacted[key] else []
    return redacted


def _is_local_or_memory_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "memory" or parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _is_real_url_forbidden(base_url: str, token: LambdaM029ArmingToken) -> bool:
    lowered = base_url.lower()
    is_real = "lambdalabs.com" in lowered or "lambda.ai" in lowered
    return is_real and not token.real_lambda_api_allowed
