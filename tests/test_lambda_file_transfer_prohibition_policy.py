from __future__ import annotations

import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.file_transfer_prohibition_policy import (
    LambdaFileTransferProhibitionPolicy,
    build_lambda_file_transfer_prohibition_policy,
)


def test_file_transfer_prohibition_denies_transfer_modes():
    report = build_lambda_file_transfer_prohibition_policy()

    assert report.scp_allowed is False
    assert report.sftp_allowed is False
    assert report.rsync_allowed is False
    assert report.upload_allowed is False
    assert report.download_allowed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_file_transfer_prohibition_rejects_scp_allowed():
    with pytest.raises(ValidationError):
        LambdaFileTransferProhibitionPolicy(scp_allowed=True)
