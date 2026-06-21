"""Project scan proving real Lambda mutation implementation is absent."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

_FORBIDDEN_PATTERNS = (
    "live-launch",
    "live-terminate",
    "allow_mutation",
    "allow-mutation",
    "launch_allowed=True",
    "launch_allowed = True",
    "ExecutableLambdaRealMutationTransport",
    "send_real_mutation_request",
    "requests.post",
    "requests.delete",
)
_FORBIDDEN_TRANSPORT_PATTERNS = (
    '"POST"',
    '"PUT"',
    '"PATCH"',
    '"DELETE"',
    "method='POST'",
    "method='DELETE'",
)


class LambdaRealMutationAbsenceAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    passed: bool
    live_client_has_launch_method: bool = True
    live_client_has_terminate_method: bool = True
    live_transport_supports_post: bool = False
    live_transport_supports_delete: bool = False
    endpoint_policy_allows_mutation: bool = False
    cli_has_live_launch_command: bool = False
    cli_has_live_terminate_command: bool = False
    real_mutation_code_detected: bool = False
    forbidden_patterns: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def audit_real_lambda_mutation_absence(
    project_root: str | Path,
) -> LambdaRealMutationAbsenceAuditReport:
    root = Path(project_root)
    lambda_dir = root / "src" / "decodilo" / "lambda_cloud"
    cloud_dir = root / "src" / "decodilo" / "cloud"
    cli_path = root / "src" / "decodilo" / "cli.py"
    offenders: list[str] = []
    transport_text = (lambda_dir / "real_read_only_transport.py").read_text(encoding="utf-8")
    live_transport_post = any(pattern in transport_text for pattern in ('"POST"', "method='POST'"))
    live_transport_delete = any(
        pattern in transport_text for pattern in ('"DELETE"', "method='DELETE'")
    )
    for base in [lambda_dir, cloud_dir]:
        for path in base.rglob("*.py"):
            if path.name.startswith("fake_"):
                continue
            if path.name in {
                "real_mutation_absence_audit.py",
                "real_mutation_skeleton_audit.py",
                "semantic_mutation_audit.py",
            }:
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in _FORBIDDEN_PATTERNS:
                if pattern in text:
                    offenders.append(f"{path.relative_to(root)}:{pattern}")
    cli_text = cli_path.read_text(encoding="utf-8")
    cli_live_launch = "live-launch" in cli_text
    cli_live_terminate = "live-terminate" in cli_text
    if cli_live_launch:
        offenders.append("src/decodilo/cli.py:live-launch")
    if cli_live_terminate:
        offenders.append("src/decodilo/cli.py:live-terminate")
    errors = sorted(set(offenders))
    return LambdaRealMutationAbsenceAuditReport(
        passed=not errors and not live_transport_post and not live_transport_delete,
        live_transport_supports_post=live_transport_post,
        live_transport_supports_delete=live_transport_delete,
        cli_has_live_launch_command=cli_live_launch,
        cli_has_live_terminate_command=cli_live_terminate,
        real_mutation_code_detected=bool(errors or live_transport_post or live_transport_delete),
        forbidden_patterns=errors,
        errors=errors,
        warnings=[
            "live read-only client exposes mutation-shaped methods that raise before transport"
        ],
    )


def write_real_lambda_mutation_absence_audit_report(
    path: str | Path,
    report: LambdaRealMutationAbsenceAuditReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
