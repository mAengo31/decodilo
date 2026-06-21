"""Provider-neutral API surface proposal for future remote artifact backends."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RemoteBackendAPIOperation(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation_id: str
    required: bool = True
    side_effecting: bool = False
    current_milestone_implemented: bool = False
    notes: list[str] = Field(default_factory=list)


class RemoteBackendAPISurface(BaseModel):
    model_config = ConfigDict(frozen=True)

    surface_schema_version: int = 1
    operations: list[RemoteBackendAPIOperation]
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def default_remote_backend_api_surface() -> RemoteBackendAPISurface:
    return RemoteBackendAPISurface(
        operations=[
            RemoteBackendAPIOperation(operation_id="put_artifact", side_effecting=True),
            RemoteBackendAPIOperation(operation_id="get_artifact"),
            RemoteBackendAPIOperation(operation_id="get_range"),
            RemoteBackendAPIOperation(operation_id="head_artifact"),
            RemoteBackendAPIOperation(operation_id="list_artifacts"),
            RemoteBackendAPIOperation(operation_id="delete_artifact", side_effecting=True),
            RemoteBackendAPIOperation(
                operation_id="conditional_put_manifest",
                side_effecting=True,
            ),
            RemoteBackendAPIOperation(operation_id="verify_artifact"),
            RemoteBackendAPIOperation(operation_id="begin_delete_transaction"),
            RemoteBackendAPIOperation(operation_id="commit_delete_transaction"),
            RemoteBackendAPIOperation(operation_id="abort_delete_transaction"),
            RemoteBackendAPIOperation(operation_id="lifecycle_mark"),
            RemoteBackendAPIOperation(operation_id="lifecycle_list"),
            RemoteBackendAPIOperation(operation_id="health_check"),
        ]
    )


def load_remote_backend_api_surface(path: str | Path) -> RemoteBackendAPISurface:
    return RemoteBackendAPISurface.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_remote_backend_api_surface(path: str | Path, surface: RemoteBackendAPISurface) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(surface.to_json(), encoding="utf-8")
