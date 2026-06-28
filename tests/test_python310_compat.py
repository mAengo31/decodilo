from __future__ import annotations

from datetime import timezone
from pathlib import Path

from decodilo.time_compat import UTC


def test_time_compat_uses_python310_timezone_utc() -> None:
    assert UTC is timezone.utc


def test_source_does_not_import_datetime_utc() -> None:
    src_root = Path(__file__).resolve().parents[1] / "src" / "decodilo"
    offenders: list[str] = []
    for path in src_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from datetime import UTC" in text or "datetime.UTC" in text:
            offenders.append(str(path.relative_to(src_root)))

    assert offenders == []

