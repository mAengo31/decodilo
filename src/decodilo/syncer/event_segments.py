"""Segmented JSONL event logs with hash-chain manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo.errors import ReplayMismatchError
from decodilo.storage.checksums import sha256_bytes, sha256_file, sha256_json
from decodilo.syncer.event_log import LogEvent, _decode_event

EVENT_SEGMENT_SCHEMA_VERSION = "v1"


class EventSegment(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    segment_id: str
    path: str
    first_event_id: str
    last_event_id: str
    first_logical_time: int
    last_logical_time: int
    event_count: int
    byte_size: int
    sha256: str
    previous_segment_sha256: str | None = None
    schema_version: str = EVENT_SEGMENT_SCHEMA_VERSION


class EventSegmentManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    segments: list[EventSegment]
    manifest_hash: str
    schema_version: str = EVENT_SEGMENT_SCHEMA_VERSION


class EventSegmentRotationPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_events_per_segment: int = Field(default=1000, gt=0)
    max_bytes_per_segment: int = Field(default=16 * 1024 * 1024, gt=0)
    rotate_on_checkpoint: bool = True


def _event_line(event: LogEvent | dict[str, Any]) -> bytes:
    if isinstance(event, LogEvent):
        return (event.to_json_line() + "\n").encode("utf-8")
    return (
        json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


class EventSegmentWriter:
    """Writes events into deterministic JSONL segments."""

    def __init__(
        self,
        *,
        root: str | Path,
        run_id: str,
        policy: EventSegmentRotationPolicy | None = None,
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.policy = policy or EventSegmentRotationPolicy()
        self._segments: list[EventSegment] = []
        self._current: list[LogEvent] = []
        self._current_bytes = 0

    def append(self, event: LogEvent, *, checkpoint_boundary: bool = False) -> None:
        line_size = len(_event_line(event))
        should_rotate = bool(
            self._current
            and (
                len(self._current) >= self.policy.max_events_per_segment
                or self._current_bytes + line_size > self.policy.max_bytes_per_segment
                or (checkpoint_boundary and self.policy.rotate_on_checkpoint)
            )
        )
        if should_rotate:
            self._flush()
        self._current.append(event)
        self._current_bytes += line_size

    def _flush(self) -> None:
        if not self._current:
            return
        index = len(self._segments)
        segment_id = f"segment-{index:06d}"
        path = self.root / f"{segment_id}.jsonl"
        payload = b"".join(_event_line(event) for event in self._current)
        path.write_bytes(payload)
        previous_hash = self._segments[-1].sha256 if self._segments else None
        segment = EventSegment(
            run_id=self.run_id,
            segment_id=segment_id,
            path=str(path),
            first_event_id=self._current[0].event_id,
            last_event_id=self._current[-1].event_id,
            first_logical_time=self._current[0].logical_time,
            last_logical_time=self._current[-1].logical_time,
            event_count=len(self._current),
            byte_size=len(payload),
            sha256=sha256_bytes(payload),
            previous_segment_sha256=previous_hash,
        )
        self._segments.append(segment)
        self._current = []
        self._current_bytes = 0

    def finalize(self) -> EventSegmentManifest:
        self._flush()
        payload = {
            "run_id": self.run_id,
            "schema_version": EVENT_SEGMENT_SCHEMA_VERSION,
            "segments": [segment.model_dump(mode="json") for segment in self._segments],
        }
        manifest = EventSegmentManifest(
            **payload,
            manifest_hash=sha256_json(payload),
        )
        (self.root / "segments_manifest.json").write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest


def validate_event_segment_manifest(
    manifest: EventSegmentManifest,
    *,
    root: str | Path | None = None,
) -> list[str]:
    errors: list[str] = []
    expected_hash = sha256_json(
        {
            "run_id": manifest.run_id,
            "schema_version": manifest.schema_version,
            "segments": [segment.model_dump(mode="json") for segment in manifest.segments],
        }
    )
    if expected_hash != manifest.manifest_hash:
        errors.append("event segment manifest_hash mismatch")
    previous_hash: str | None = None
    base = Path(root) if root is not None else None
    for segment in manifest.segments:
        path = Path(segment.path)
        if base is not None and not path.is_absolute():
            path = base / path
        if segment.previous_segment_sha256 != previous_hash:
            errors.append(f"{segment.segment_id} previous hash does not chain")
        if not path.exists():
            errors.append(f"missing event segment: {path}")
            previous_hash = segment.sha256
            continue
        if path.stat().st_size != segment.byte_size:
            errors.append(f"{segment.segment_id} byte_size mismatch")
        actual_hash = sha256_file(path)
        if actual_hash != segment.sha256:
            errors.append(f"{segment.segment_id} sha256 mismatch")
        previous_hash = segment.sha256
    return errors


class EventSegmentReader:
    """Validating reader for segmented event logs."""

    def __init__(self, manifest_path: str | Path) -> None:
        self.manifest_path = Path(manifest_path)
        self.manifest = EventSegmentManifest.model_validate_json(
            self.manifest_path.read_text(encoding="utf-8")
        )

    def validate(self) -> None:
        errors = validate_event_segment_manifest(
            self.manifest,
            root=self.manifest_path.parent,
        )
        if errors:
            raise ReplayMismatchError("; ".join(errors))

    def iter_events(self) -> list[LogEvent]:
        self.validate()
        events: list[LogEvent] = []
        for segment in self.manifest.segments:
            path = Path(segment.path)
            if not path.is_absolute():
                path = self.manifest_path.parent / path
            with path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if line.strip():
                        events.append(
                            _decode_event(
                                line,
                                source=f"{path}:{line_number}",
                            )
                        )
        return events


def segment_events_from_jsonl(
    *,
    event_log_path: str | Path,
    out_dir: str | Path,
    policy: EventSegmentRotationPolicy | None = None,
) -> EventSegmentManifest:
    from decodilo.syncer.event_log import read_event_log

    events = list(read_event_log(event_log_path))
    run_id = events[0].run_id if events else "unknown"
    writer = EventSegmentWriter(root=out_dir, run_id=run_id, policy=policy)
    for event in events:
        writer.append(
            event,
            checkpoint_boundary=event.event_type.value.endswith("checkpoint_written"),
        )
    return writer.finalize()
