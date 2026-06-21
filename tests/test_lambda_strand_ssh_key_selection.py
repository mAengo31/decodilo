from lambda_m037r_helpers import discovery

from decodilo.lambda_cloud.strand_ssh_key_selection import select_existing_lambda_ssh_key


def test_existing_ssh_key_selected_from_read_only_discovery():
    report = select_existing_lambda_ssh_key(discovery=discovery())

    assert report.selection_passed is True
    assert report.discovered_ssh_key_count == 1
    assert report.selected_ssh_key_name_for_payload == "existing-key"
    assert report.selected_ssh_key_name_redacted_or_hash.startswith("sha256:")
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_no_existing_ssh_key_blocks_selection():
    report = select_existing_lambda_ssh_key(discovery=discovery(ssh_key_names=()))

    assert report.selection_passed is False
    assert "no existing SSH key names discovered or selected" in report.errors


def test_public_key_material_is_not_stored():
    report = select_existing_lambda_ssh_key(discovery=discovery())

    assert report.raw_public_key_material_present is False
    assert report.create_key_requested is False
    assert report.delete_key_requested is False
