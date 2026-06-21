"""Authorization scope planning for future remote artifact backends."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

REQUIRED_REMOTE_BACKEND_SCOPES = {
    "syncer_manifest_read_write",
    "learner_fragment_write",
    "learner_global_update_read",
    "replay_artifact_read",
    "gc_delete",
}


class AuthScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    scope_id: str
    principal: str
    allowed_operations: list[str]
    resource_pattern: str
    notes: list[str] = Field(default_factory=list)


class AuthScopePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_schema_version: int = 1
    scopes: list[AuthScope] = Field(default_factory=list)
    least_privilege_required: bool = True
    wildcard_scopes_allowed: bool = False


class AuthScopeAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    scope_ids: list[str]
    missing_scopes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def default_auth_scope_policy() -> AuthScopePolicy:
    return AuthScopePolicy(
        scopes=[
            AuthScope(
                scope_id="syncer_manifest_read_write",
                principal="syncer",
                allowed_operations=["manifest:read", "manifest:write"],
                resource_pattern="artifacts/manifests/*",
            ),
            AuthScope(
                scope_id="learner_fragment_write",
                principal="learner",
                allowed_operations=["artifact:write"],
                resource_pattern="artifacts/fragments/*",
            ),
            AuthScope(
                scope_id="learner_global_update_read",
                principal="learner",
                allowed_operations=["artifact:read"],
                resource_pattern="artifacts/global-updates/*",
            ),
            AuthScope(
                scope_id="replay_artifact_read",
                principal="replay",
                allowed_operations=["artifact:read", "artifact:range-read"],
                resource_pattern="artifacts/*",
            ),
            AuthScope(
                scope_id="gc_delete",
                principal="gc",
                allowed_operations=["artifact:delete"],
                resource_pattern="artifacts/gc-eligible/*",
            ),
        ]
    )


def evaluate_auth_scope_policy(
    policy: AuthScopePolicy,
    *,
    lifecycle_delete_required: bool = True,
) -> AuthScopeAuditReport:
    scope_ids = [scope.scope_id for scope in policy.scopes]
    required = set(REQUIRED_REMOTE_BACKEND_SCOPES)
    if not lifecycle_delete_required:
        required.discard("gc_delete")
    missing = sorted(required - set(scope_ids))
    errors: list[str] = []
    warnings: list[str] = []
    if missing:
        errors.append(f"missing required auth scopes: {missing}")
    if policy.wildcard_scopes_allowed:
        warnings.append("wildcard scopes weaken least-privilege guarantees")
    if policy.least_privilege_required:
        for scope in policy.scopes:
            if "*" in scope.allowed_operations or scope.resource_pattern.strip() == "*":
                errors.append(f"scope {scope.scope_id} is not least-privilege")
    return AuthScopeAuditReport(
        passed=not errors,
        scope_ids=scope_ids,
        missing_scopes=missing,
        errors=errors,
        warnings=warnings,
    )


def load_auth_scope_policy(path: str | Path) -> AuthScopePolicy:
    return AuthScopePolicy.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_auth_scope_audit_report(path: str | Path, report: AuthScopeAuditReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
