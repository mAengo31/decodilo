from __future__ import annotations

import pytest
from lambda_m053_helpers import write_ssh_key_selection
from pydantic import ValidationError

from decodilo.lambda_cloud.ssh_private_key_reference_policy import (
    build_lambda_ssh_private_key_reference_policy_from_path,
)


def test_ssh_private_key_reference_policy_allows_redacted_symbolic_reference(tmp_path):
    selection = write_ssh_key_selection(tmp_path / "ssh-selection.json")

    report = build_lambda_ssh_private_key_reference_policy_from_path(selection)

    assert report.key_reference_policy_status == "policy_defined"
    assert report.selected_ssh_key_hash == "sha256:e8bd9b2e6fc17b09"
    assert report.public_report_key_reference == "<redacted-private-key-reference>"
    assert report.private_key_material_serialized is False
    assert report.credential_used_in_m054a is False
    assert report.launch_allowed is False


def test_ssh_private_key_reference_policy_rejects_key_material(tmp_path):
    selection = write_ssh_key_selection(
        tmp_path / "ssh-selection.json",
        private_material=True,
    )

    with pytest.raises(ValidationError):
        build_lambda_ssh_private_key_reference_policy_from_path(selection)
