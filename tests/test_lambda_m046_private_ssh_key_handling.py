from __future__ import annotations

import pytest
from lambda_m037r_helpers import ssh_selection
from lambda_m046a_helpers import RAW_TEST_SSH_KEY_NAME, run_m046_fake

from decodilo.lambda_cloud.strand_ssh_key_selection import (
    LambdaExistingSSHKeySelectionReport,
)


def test_m046_public_reports_redact_private_ssh_key(tmp_path):
    result = run_m046_fake(tmp_path)

    assert result.returncode == 0
    for name in [
        "report.json",
        "capacity-selected-gates.json",
        "capacity-selected-execution-gate.json",
    ]:
        text = (result.workdir / name).read_text(encoding="utf-8")  # type: ignore[attr-defined]
        assert RAW_TEST_SSH_KEY_NAME not in text
        assert "sha256:" in text


def test_m046_missing_private_ssh_key_name_blocks(tmp_path):
    result = run_m046_fake(tmp_path, missing_raw_key=True)

    assert result.returncode != 0
    assert "raw_existing_ssh_key_name_missing" in result.stderr


def test_m046_raw_public_key_material_rejected():
    with pytest.raises(ValueError, match="raw public key material"):
        LambdaExistingSSHKeySelectionReport.model_validate(
            {
                **ssh_selection().model_dump(mode="json"),
                "raw_public_key_material_present": True,
            }
        )
