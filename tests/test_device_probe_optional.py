import pytest

from decodilo.trainer.device_probe import available_devices


@pytest.mark.hardware_optional
def test_device_probe_reports_cpu_without_requiring_torch() -> None:
    devices = available_devices()

    assert devices["cpu"] is True
    assert "cuda" in devices
    assert "mps" in devices

