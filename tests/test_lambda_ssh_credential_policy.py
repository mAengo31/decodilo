from __future__ import annotations

import pytest
from lambda_m053_helpers import write_ssh_key_selection
from pydantic import ValidationError

from decodilo.lambda_cloud.ssh_credential_policy import (
    build_lambda_ssh_credential_policy_from_path,
)


def test_ssh_credential_policy_accepts_existing_key_hash(tmp_path):
    selection = write_ssh_key_selection(tmp_path / "ssh-selection.json")

    report = build_lambda_ssh_credential_policy_from_path(selection)

    assert report.credential_policy_status == "policy_defined"
    assert report.existing_key_required is True
    assert report.key_creation_allowed is False
    assert report.selected_ssh_key_hash == "sha256:e8bd9b2e6fc17b09"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_credential_policy_rejects_private_key_material(tmp_path):
    selection = write_ssh_key_selection(
        tmp_path / "ssh-selection.json",
        private_material=True,
    )

    with pytest.raises(ValidationError):
        build_lambda_ssh_credential_policy_from_path(selection)
