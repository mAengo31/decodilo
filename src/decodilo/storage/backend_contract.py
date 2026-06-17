"""Backend contract checks for local and disabled artifact backends."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.artifact_backend import ArtifactBackend
from decodilo.storage.disabled_remote_backend import RemoteBackendDisabledError


class BackendContractCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool
    message: str = ""


class BackendContractReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend_type: str
    usable: bool
    remote_backend_enabled: bool
    checks: list[BackendContractCheck] = Field(default_factory=list)
    capabilities: dict[str, Any] = Field(default_factory=dict)


def check_backend_contract(backend: ArtifactBackend) -> BackendContractReport:
    capabilities = backend.capabilities()
    checks: list[BackendContractCheck] = [
        BackendContractCheck(
            name="capabilities_serialize",
            passed=bool(capabilities.model_dump(mode="json")["backend_type"]),
        )
    ]
    if capabilities.remote:
        try:
            backend.list_refs()
        except RemoteBackendDisabledError:
            checks.append(
                BackendContractCheck(
                    name="remote_disabled",
                    passed=True,
                    message="remote backend operations are disabled",
                )
            )
        else:
            checks.append(
                BackendContractCheck(
                    name="remote_disabled",
                    passed=False,
                    message="remote backend unexpectedly allowed list_refs",
                )
            )
    else:
        ref = backend.write_bytes(artifact_id="contract-sample", data=b"contract")
        checks.append(
            BackendContractCheck(
                name="roundtrip",
                passed=backend.read_bytes(ref) == b"contract",
            )
        )
    usable = all(check.passed for check in checks) and capabilities.read_supported
    return BackendContractReport(
        backend_type=capabilities.backend_type,
        usable=usable and not capabilities.remote,
        remote_backend_enabled=capabilities.remote and capabilities.read_supported,
        checks=checks,
        capabilities=capabilities.model_dump(mode="json"),
    )
