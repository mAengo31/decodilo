import json

from decodilo.lambda_cloud.ssh_provider_key_attachment_diagnostic import (
    build_lambda_ssh_provider_key_attachment_diagnostic_from_paths,
)


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_provider_key_attachment_current_style_is_consistent(tmp_path):
    selection = tmp_path / "selection.json"
    provider = tmp_path / "provider.json"
    launch = tmp_path / "launch.json"
    _write(
        selection,
        {
            "selection_passed": True,
            "selected_ssh_key_name_redacted_or_hash": "sha256:keyhash",
        },
    )
    _write(
        provider,
        {"data": [{"name": "sha256:keyhash", "key_id": "redacted", "fingerprint": "fp"}]},
    )
    _write(launch, {"selected_ssh_key_hash": "sha256:keyhash"})

    report = build_lambda_ssh_provider_key_attachment_diagnostic_from_paths(
        ssh_key_selection=selection,
        launch_report=launch,
        provider_key_list=provider,
        local_private_key_matches_public_identity=True,
    )

    assert report.key_attachment_diagnostic_status == "evidence_consistent"
    assert report.provider_user_id_field_present is False
    assert report.provider_user_id_field_missing_not_blocking is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_provider_key_attachment_mismatch_blocks(tmp_path):
    selection = tmp_path / "selection.json"
    launch = tmp_path / "launch.json"
    _write(selection, {"selected_ssh_key_name_redacted_or_hash": "sha256:a"})
    _write(launch, {"selected_ssh_key_hash": "sha256:b"})

    report = build_lambda_ssh_provider_key_attachment_diagnostic_from_paths(
        ssh_key_selection=selection,
        launch_report=launch,
    )

    assert report.key_attachment_diagnostic_status == "mismatch"
    assert "selected_launch_key_hash_mismatch" in report.blockers
