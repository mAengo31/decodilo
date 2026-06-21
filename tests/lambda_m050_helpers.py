from __future__ import annotations

from pathlib import Path

from lambda_m047_helpers import write_m047_inputs

from decodilo.lambda_cloud.bootstrap_evidence_schema import (
    build_lambda_bootstrap_evidence_schema,
    write_lambda_bootstrap_evidence_schema,
)
from decodilo.lambda_cloud.bootstrap_risk_review import (
    build_lambda_bootstrap_risk_review_from_paths,
    write_lambda_bootstrap_risk_review,
)
from decodilo.lambda_cloud.m050_report import (
    build_lambda_m050_report_from_paths,
    write_lambda_m050_report,
)
from decodilo.lambda_cloud.m051_bootstrap_authorization import (
    build_lambda_m051_bootstrap_authorization_from_paths,
    write_lambda_m051_bootstrap_authorization,
)
from decodilo.lambda_cloud.m051_bootstrap_runbook_preview import (
    build_lambda_m051_bootstrap_runbook_preview_from_paths,
    write_lambda_m051_bootstrap_runbook_preview,
)
from decodilo.lambda_cloud.no_training_policy import (
    build_lambda_no_training_policy,
    write_lambda_no_training_policy,
)
from decodilo.lambda_cloud.package_install_policy import (
    build_lambda_package_install_policy,
    write_lambda_package_install_policy,
)
from decodilo.lambda_cloud.remote_access_policy import (
    build_lambda_remote_access_policy,
    write_lambda_remote_access_policy,
)
from decodilo.lambda_cloud.remote_bootstrap_scope import (
    build_lambda_remote_bootstrap_scope,
    write_lambda_remote_bootstrap_scope,
)
from decodilo.lambda_cloud.remote_command_allowlist import (
    build_lambda_remote_command_allowlist,
    write_lambda_remote_command_allowlist,
)
from decodilo.lambda_cloud.ssh_operator_approval import (
    build_lambda_ssh_operator_approval,
    write_lambda_ssh_operator_approval,
)


def write_m050_inputs(base: Path) -> dict[str, Path]:
    m047 = write_m047_inputs(base / "m047")
    paths = {
        **m047,
        "scope": base / "bootstrap-scope.json",
        "access": base / "bootstrap-access-policy.json",
        "ssh": base / "bootstrap-ssh-approval.json",
        "commands": base / "bootstrap-command-allowlist.json",
        "install": base / "bootstrap-package-install-policy.json",
        "training": base / "bootstrap-no-training-policy.json",
        "evidence_schema": base / "bootstrap-evidence-schema.json",
        "risk": base / "bootstrap-risk-review.json",
        "authorization": base / "m051-bootstrap-authorization.json",
        "runbook": base / "m051-bootstrap-runbook-preview.json",
        "m050": base / "m050-report.json",
    }
    scope = build_lambda_remote_bootstrap_scope()
    write_lambda_remote_bootstrap_scope(paths["scope"], scope)
    access = build_lambda_remote_access_policy()
    write_lambda_remote_access_policy(paths["access"], access)
    ssh = build_lambda_ssh_operator_approval(decline_ssh=True)
    write_lambda_ssh_operator_approval(paths["ssh"], ssh)
    commands = build_lambda_remote_command_allowlist(profile="metadata-only")
    write_lambda_remote_command_allowlist(paths["commands"], commands)
    install = build_lambda_package_install_policy()
    write_lambda_package_install_policy(paths["install"], install)
    training = build_lambda_no_training_policy()
    write_lambda_no_training_policy(paths["training"], training)
    evidence = build_lambda_bootstrap_evidence_schema()
    write_lambda_bootstrap_evidence_schema(paths["evidence_schema"], evidence)
    risk = build_lambda_bootstrap_risk_review_from_paths(
        scope=paths["scope"],
        access_policy=paths["access"],
        ssh_approval=paths["ssh"],
        command_allowlist=paths["commands"],
        package_install_policy=paths["install"],
        no_training_policy=paths["training"],
        evidence_schema=paths["evidence_schema"],
        lifecycle_closeout=paths["closeout"],
    )
    write_lambda_bootstrap_risk_review(paths["risk"], risk)
    authorization = build_lambda_m051_bootstrap_authorization_from_paths(
        scope=paths["scope"],
        risk_review=paths["risk"],
    )
    write_lambda_m051_bootstrap_authorization(paths["authorization"], authorization)
    runbook = build_lambda_m051_bootstrap_runbook_preview_from_paths(
        authorization=paths["authorization"]
    )
    write_lambda_m051_bootstrap_runbook_preview(paths["runbook"], runbook)
    report = build_lambda_m050_report_from_paths(
        scope=paths["scope"],
        access_policy=paths["access"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )
    write_lambda_m050_report(paths["m050"], report)
    return paths
