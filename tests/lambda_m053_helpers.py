from __future__ import annotations

import json
from pathlib import Path

from lambda_m052_helpers import write_m052_inputs

from decodilo.lambda_cloud.file_transfer_prohibition_policy import (
    build_lambda_file_transfer_prohibition_policy,
    write_lambda_file_transfer_prohibition_policy,
)
from decodilo.lambda_cloud.m053_report import (
    build_lambda_m053_report_from_paths,
    write_lambda_m053_report,
)
from decodilo.lambda_cloud.m054_ssh_connectivity_authorization import (
    build_lambda_m054_ssh_connectivity_authorization_from_path,
    write_lambda_m054_ssh_connectivity_authorization,
)
from decodilo.lambda_cloud.m054_ssh_connectivity_runbook_preview import (
    build_lambda_m054_ssh_connectivity_runbook_preview_from_path,
    write_lambda_m054_ssh_connectivity_runbook_preview,
)
from decodilo.lambda_cloud.no_training_policy import (
    build_lambda_no_training_policy,
    write_lambda_no_training_policy,
)
from decodilo.lambda_cloud.package_install_policy import (
    build_lambda_package_install_policy,
    write_lambda_package_install_policy,
)
from decodilo.lambda_cloud.port_forwarding_prohibition_policy import (
    build_lambda_port_forwarding_prohibition_policy,
    write_lambda_port_forwarding_prohibition_policy,
)
from decodilo.lambda_cloud.remote_command_prohibition_policy import (
    build_lambda_remote_command_prohibition_policy,
    write_lambda_remote_command_prohibition_policy,
)
from decodilo.lambda_cloud.ssh_client_policy import (
    build_lambda_ssh_client_policy,
    write_lambda_ssh_client_policy,
)
from decodilo.lambda_cloud.ssh_connectivity_evidence_schema import (
    build_lambda_ssh_connectivity_evidence_schema,
    write_lambda_ssh_connectivity_evidence_schema,
)
from decodilo.lambda_cloud.ssh_connectivity_operator_approval import (
    build_lambda_ssh_connectivity_operator_approval,
    write_lambda_ssh_connectivity_operator_approval,
)
from decodilo.lambda_cloud.ssh_connectivity_risk_review import (
    build_lambda_ssh_connectivity_risk_review_from_paths,
    write_lambda_ssh_connectivity_risk_review,
)
from decodilo.lambda_cloud.ssh_connectivity_scope import (
    build_lambda_ssh_connectivity_scope,
    write_lambda_ssh_connectivity_scope,
)
from decodilo.lambda_cloud.ssh_credential_policy import (
    build_lambda_ssh_credential_policy_from_path,
    write_lambda_ssh_credential_policy,
)


def write_ssh_key_selection(path: Path, *, private_material: bool = False) -> Path:
    payload = {
        "billable_action_performed": False,
        "create_key_requested": False,
        "delete_key_requested": False,
        "raw_public_key_material_present": False,
        "selected_ssh_key_name_redacted_or_hash": "sha256:e8bd9b2e6fc17b09",
        "selection_passed": True,
    }
    if private_material:
        payload["private_key"] = "-----BEGIN OPENSSH PRIVATE KEY-----"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_m053_inputs(
    base: Path,
    *,
    approve: bool = False,
    decline: bool = False,
) -> dict[str, Path]:
    paths = write_m052_inputs(base / "m052")
    paths.update(
        {
            "ssh_selection": base / "ssh-selection.json",
            "scope": base / "ssh-scope.json",
            "credential": base / "credential.json",
            "client": base / "client.json",
            "evidence_schema": base / "evidence-schema.json",
            "operator": base / "operator.json",
            "remote_prohibition": base / "remote-prohibition.json",
            "file_prohibition": base / "file-prohibition.json",
            "port_prohibition": base / "port-prohibition.json",
            "package": base / "package.json",
            "training": base / "training.json",
            "risk": base / "risk.json",
            "authorization": base / "authorization.json",
            "runbook": base / "runbook.json",
            "m053": base / "m053.json",
            "m053a": base / "m053a.json",
        }
    )
    write_ssh_key_selection(paths["ssh_selection"])
    write_lambda_ssh_connectivity_scope(paths["scope"], build_lambda_ssh_connectivity_scope())
    write_lambda_ssh_credential_policy(
        paths["credential"],
        build_lambda_ssh_credential_policy_from_path(paths["ssh_selection"]),
    )
    write_lambda_ssh_client_policy(paths["client"], build_lambda_ssh_client_policy())
    write_lambda_ssh_connectivity_evidence_schema(
        paths["evidence_schema"],
        build_lambda_ssh_connectivity_evidence_schema(),
    )
    write_lambda_ssh_connectivity_operator_approval(
        paths["operator"],
        build_lambda_ssh_connectivity_operator_approval(
            approve_future_m054=approve,
            decline=decline,
            acknowledge_all=approve,
        ),
    )
    write_lambda_remote_command_prohibition_policy(
        paths["remote_prohibition"],
        build_lambda_remote_command_prohibition_policy(),
    )
    write_lambda_file_transfer_prohibition_policy(
        paths["file_prohibition"],
        build_lambda_file_transfer_prohibition_policy(),
    )
    write_lambda_port_forwarding_prohibition_policy(
        paths["port_prohibition"],
        build_lambda_port_forwarding_prohibition_policy(),
    )
    write_lambda_package_install_policy(paths["package"], build_lambda_package_install_policy())
    write_lambda_no_training_policy(paths["training"], build_lambda_no_training_policy())
    risk = build_lambda_ssh_connectivity_risk_review_from_paths(
        scope=paths["scope"],
        credential_policy=paths["credential"],
        client_policy=paths["client"],
        evidence_schema=paths["evidence_schema"],
        operator_approval=paths["operator"],
        remote_command_prohibition=paths["remote_prohibition"],
        file_transfer_prohibition=paths["file_prohibition"],
        port_forwarding_prohibition=paths["port_prohibition"],
        package_install_policy=paths["package"],
        no_training_policy=paths["training"],
        m052_report=paths["m052"],
    )
    write_lambda_ssh_connectivity_risk_review(paths["risk"], risk)
    auth = build_lambda_m054_ssh_connectivity_authorization_from_path(paths["risk"])
    write_lambda_m054_ssh_connectivity_authorization(paths["authorization"], auth)
    runbook = build_lambda_m054_ssh_connectivity_runbook_preview_from_path(paths["authorization"])
    write_lambda_m054_ssh_connectivity_runbook_preview(paths["runbook"], runbook)
    report = build_lambda_m053_report_from_paths(
        scope=paths["scope"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )
    write_lambda_m053_report(paths["m053"], report)
    return paths
