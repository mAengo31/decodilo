import pytest

from decodilo.runtime.lifecycle_faults import corrupt_text_file, remove_file

pytestmark = [pytest.mark.lifecycle, pytest.mark.unit]


def test_lifecycle_fault_helpers_corrupt_and_remove_files(tmp_path) -> None:
    target = tmp_path / "target.json"
    target.write_text("{}\n", encoding="utf-8")

    corrupt_text_file(target)
    assert target.read_text(encoding="utf-8") == "corrupted"
    remove_file(target)
    assert not target.exists()

