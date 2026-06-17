"""Named local soak profiles."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SoakProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    learners: int = Field(gt=0)
    steps: int = Field(gt=0)
    min_quorum: int = Field(gt=0)
    vector_dim: int = Field(gt=0)
    fragments: int = Field(gt=0)
    local_steps_per_sync: int = Field(gt=0)
    cases: list[str]
    trainer: str = "numpy_convex"
    optional: bool = False


SOAK_PROFILES: dict[str, SoakProfile] = {
    "ci": SoakProfile(
        name="ci",
        learners=3,
        steps=50,
        min_quorum=2,
        vector_dim=4,
        fragments=2,
        local_steps_per_sync=10,
        cases=["baseline", "slow_restore"],
    ),
    "local_medium": SoakProfile(
        name="local_medium",
        learners=6,
        steps=300,
        min_quorum=3,
        vector_dim=8,
        fragments=3,
        local_steps_per_sync=10,
        cases=["baseline", "slow_restore", "learner_restart"],
    ),
    "local_faulty": SoakProfile(
        name="local_faulty",
        learners=4,
        steps=160,
        min_quorum=2,
        vector_dim=4,
        fragments=3,
        local_steps_per_sync=10,
        cases=["learner_kill", "learner_restart", "slow_restore", "syncer_restart", "backpressure"],
    ),
    "torch_cpu_ci": SoakProfile(
        name="torch_cpu_ci",
        learners=2,
        steps=20,
        min_quorum=1,
        vector_dim=4,
        fragments=1,
        local_steps_per_sync=5,
        cases=["baseline"],
        trainer="torch_causal_lm",
        optional=True,
    ),
    "torch_cpu_medium": SoakProfile(
        name="torch_cpu_medium",
        learners=2,
        steps=80,
        min_quorum=1,
        vector_dim=4,
        fragments=1,
        local_steps_per_sync=5,
        cases=["baseline", "slow_restore"],
        trainer="torch_causal_lm",
        optional=True,
    ),
    "chunked_ci": SoakProfile(
        name="chunked_ci",
        learners=2,
        steps=50,
        min_quorum=1,
        vector_dim=4,
        fragments=1,
        local_steps_per_sync=10,
        cases=["baseline", "syncer_restart"],
    ),
    "binary_chunked_ci": SoakProfile(
        name="binary_chunked_ci",
        learners=2,
        steps=50,
        min_quorum=1,
        vector_dim=4,
        fragments=1,
        local_steps_per_sync=10,
        cases=["baseline", "syncer_restart"],
    ),
}


def get_soak_profile(name: str) -> SoakProfile:
    try:
        return SOAK_PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"unknown soak profile {name!r}") from exc


def list_soak_profiles() -> list[dict]:
    return [profile.model_dump(mode="json") for profile in SOAK_PROFILES.values()]
