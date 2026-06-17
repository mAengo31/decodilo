"""Event segment compaction helpers."""

from __future__ import annotations

from pathlib import Path

from decodilo.syncer.event_segments import (
    EventSegmentManifest,
    EventSegmentRotationPolicy,
    segment_events_from_jsonl,
)


def compact_event_log_to_segments(
    *,
    event_log_path: str | Path,
    out_dir: str | Path,
    max_events_per_segment: int = 10,
) -> EventSegmentManifest:
    return segment_events_from_jsonl(
        event_log_path=event_log_path,
        out_dir=out_dir,
        policy=EventSegmentRotationPolicy(max_events_per_segment=max_events_per_segment),
    )

