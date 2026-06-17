"""Runtime wrapper for trainer compatibility matrix reports."""

from __future__ import annotations

import json
from pathlib import Path

from decodilo.trainer.compatibility import (
    TrainerCompatibilityMatrix,
    build_trainer_compatibility_matrix,
    check_trainer_compatibility,
    trainer_names,
)


def list_trainers(*, include_optional: bool = True) -> list[dict]:
    return [
        {"trainer": name, "optional": name.startswith("torch_")}
        for name in trainer_names(include_optional=include_optional)
    ]


def run_trainer_check(*, trainer: str, workdir: str | Path) -> dict:
    Path(workdir).mkdir(parents=True, exist_ok=True)
    result = check_trainer_compatibility(trainer)
    path = Path(workdir) / f"{trainer}-compatibility.json"
    path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"report_path": str(path), **result.model_dump(mode="json")}


def run_trainer_matrix(
    *,
    workdir: str | Path,
    include_optional: bool = False,
) -> TrainerCompatibilityMatrix:
    Path(workdir).mkdir(parents=True, exist_ok=True)
    matrix = build_trainer_compatibility_matrix(include_optional=include_optional)
    (Path(workdir) / "trainer_matrix.json").write_text(
        json.dumps(matrix.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return matrix
