"""Semantic audit proving live Lambda mutation execution remains absent."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

_MUTATION_NAMES = {
    "launch_instance",
    "terminate_instance",
    "restart_instance",
    "create_ssh_key",
    "delete_ssh_key",
    "create_filesystem",
    "delete_filesystem",
}
_NON_GET_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_FAKE_PREFIXES = ("fake_",)
_ALLOWLIST_MODULES = {
    "client_interface.py",
    "disabled_client.py",
    "disabled_real_mutation_transport.py",
    "read_only_client.py",
    "real_mutation_skeleton_client.py",
    "fake_mutation_api.py",
    "fake_mutation_transport.py",
    "fake_mutation_server.py",
}
_AUDIT_MODULES = {
    "real_mutation_absence_audit.py",
    "real_mutation_skeleton_audit.py",
    "semantic_mutation_audit.py",
}


class LambdaSemanticMutationAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    passed: bool
    scanned_files: int
    allowlisted_findings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def audit_lambda_semantic_mutation_absence(
    project_root: str | Path,
) -> LambdaSemanticMutationAuditReport:
    root = Path(project_root)
    files = [
        *sorted((root / "src" / "decodilo" / "lambda_cloud").glob("*.py")),
        root / "src" / "decodilo" / "cli.py",
    ]
    blockers: list[str] = []
    allowed: list[str] = []
    for path in files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        rel = str(path.relative_to(root))
        if path.name not in _AUDIT_MODULES:
            blockers.extend(_forbidden_literal_assignments(rel, text))
        if path.name == "real_read_only_transport.py":
            blockers.extend(_non_get_live_transport_usage(rel, text))
        if path.name == "cli.py":
            blockers.extend(_forbidden_live_cli(rel, text))
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            blockers.append(f"{rel}: syntax error during audit: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                finding = f"{rel}:{node.name}"
                if node.name in _MUTATION_NAMES:
                    if _module_allowlisted(path) or _function_immediately_raises(node):
                        allowed.append(finding)
                    else:
                        blockers.append(f"executable live mutation-like method: {finding}")
            if isinstance(node, ast.Call):
                blockers.extend(_non_get_call_findings(rel, node, path))
    return LambdaSemanticMutationAuditReport(
        passed=not blockers,
        scanned_files=sum(1 for path in files if path.exists()),
        allowlisted_findings=allowed,
        blockers=blockers,
        warnings=["Semantic audit is static evidence and does not enable launch."],
    )


def _module_allowlisted(path: Path) -> bool:
    return path.name in _ALLOWLIST_MODULES or path.name.startswith(_FAKE_PREFIXES)


def _function_immediately_raises(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = [stmt for stmt in node.body if not isinstance(stmt, ast.Expr) or not _is_doc(stmt)]
    return bool(body and isinstance(body[0], ast.Raise))


def _is_doc(stmt: ast.Expr) -> bool:
    return isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)


def _forbidden_literal_assignments(rel: str, text: str) -> list[str]:
    patterns = [
        "launch_allowed" + "=True",
        "launch_allowed" + " = True",
        "launch_ready" + "=True",
        "launch_ready" + " = True",
        "real_mutation_enabled" + "=True",
        "real_mutation_enabled" + " = True",
        "mutation_armed" + "=True",
        "mutation_armed" + " = True",
        "real_launch_" + "approved",
    ]
    return [
        f"{rel}: forbidden enabled literal {pattern}"
        for pattern in patterns
        if pattern in text
    ]


def _non_get_live_transport_usage(rel: str, text: str) -> list[str]:
    findings = []
    for method in _NON_GET_METHODS:
        if f'"{method}"' in text or f"'{method}'" in text:
            findings.append(f"{rel}: live transport references non-GET {method}")
    return findings


def _forbidden_live_cli(rel: str, text: str) -> list[str]:
    forbidden = ["live-launch", "live-terminate", "live-restart"]
    return [f"{rel}: forbidden CLI command {item}" for item in forbidden if item in text]


def _non_get_call_findings(rel: str, node: ast.Call, path: Path) -> list[str]:
    if path.name != "real_read_only_transport.py":
        return []
    func = node.func
    attr = func.attr.lower() if isinstance(func, ast.Attribute) else ""
    if attr in {"post", "put", "patch", "delete"}:
        return [f"{rel}: live transport call uses {attr.upper()}"]
    return []


def load_lambda_semantic_mutation_audit_report(
    path: str | Path,
) -> LambdaSemanticMutationAuditReport:
    return LambdaSemanticMutationAuditReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_semantic_mutation_audit_report(
    path: str | Path,
    report: LambdaSemanticMutationAuditReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
