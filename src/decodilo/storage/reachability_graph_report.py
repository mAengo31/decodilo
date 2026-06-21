"""Compact JSON reachability graph reports for local artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.artifact_index import build_artifact_index
from decodilo.storage.reachability import build_reachability_graph


class ReachabilityGraphReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    nodes: list[dict[str, Any]]
    edges: list[dict[str, str]]
    root_nodes: list[str]
    unreachable_nodes: list[str]
    protected_nodes: list[str]
    gc_eligible_nodes: list[str]
    referrer_summary: dict[str, int]
    top_referrers: list[dict[str, Any]]
    unresolved_references: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def build_reachability_graph_report(
    *,
    workdir: str | Path,
    allow_incomplete: bool = True,
) -> ReachabilityGraphReport:
    index = build_artifact_index(workdir)
    graph = build_reachability_graph(
        workdir=workdir,
        index=index,
        allow_incomplete=allow_incomplete,
    )
    roots = sorted(
        path
        for path in graph.protected
        if Path(path).name in {"run_spec.json", "report.json", "artifacts.json"}
    )
    nodes = [
        {
            "path": path,
            "size_bytes": record.size_bytes,
            "artifact_type": record.artifact_type,
            "reachable": path in graph.live or path in graph.retained or path in graph.protected,
            "protected": path in graph.protected,
            "temporary": path in graph.temporary,
        }
        for path, record in sorted(index.artifacts.items())
    ]
    edges: list[dict[str, str]] = []
    for root in roots:
        for target in sorted(graph.live | graph.retained | graph.protected):
            if target != root:
                edges.append({"from": root, "to": target})
    referrer_counts: dict[str, int] = {}
    for edge in edges:
        referrer_counts[edge["from"]] = referrer_counts.get(edge["from"], 0) + 1
    top_referrers = [
        {"path": path, "outgoing_refs": count}
        for path, count in sorted(
            referrer_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:10]
    ]
    errors = []
    if graph.unresolved_required and not allow_incomplete:
        errors.extend(f"unresolved reference: {path}" for path in sorted(graph.unresolved_required))
    return ReachabilityGraphReport(
        nodes=nodes,
        edges=edges,
        root_nodes=roots,
        unreachable_nodes=sorted(graph.orphaned),
        protected_nodes=sorted(graph.protected),
        gc_eligible_nodes=sorted(graph.orphaned | graph.temporary),
        referrer_summary=referrer_counts,
        top_referrers=top_referrers,
        unresolved_references=sorted(graph.unresolved_required),
        errors=errors,
    )


def write_reachability_graph_report(path: str | Path, report: ReachabilityGraphReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
