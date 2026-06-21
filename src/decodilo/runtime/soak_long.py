"""Helpers for guarded longer local soak profiles."""

from __future__ import annotations

from decodilo.errors import InvariantViolation
from decodilo.runtime.soak_profiles import SoakProfile


def require_long_flag_for_profile(profile: SoakProfile, *, long: bool) -> None:
    if profile.requires_long and not long:
        raise InvariantViolation(f"soak profile {profile.name!r} requires --long")

