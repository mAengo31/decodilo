"""Round-triggered local runtime chaos actions."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class RoundAction:
    learner_id: str
    after_round: int


@dataclass(frozen=True)
class SlowLearnerAction(RoundAction):
    factor: float


def parse_round_action(value: str | None) -> RoundAction | None:
    if value is None:
        return None
    learner_id, _, rest = value.partition(":")
    if not learner_id or not rest.startswith("after-round="):
        raise argparse.ArgumentTypeError("expected learner-id:after-round=N")
    return RoundAction(learner_id=learner_id, after_round=int(rest.split("=", 1)[1]))


def parse_slow_action(value: str | None) -> SlowLearnerAction | None:
    if value is None:
        return None
    parts = value.split(":")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("expected learner-id:factor=X:after-round=N")
    learner_id = parts[0]
    factor_text = next((part for part in parts[1:] if part.startswith("factor=")), None)
    round_text = next((part for part in parts[1:] if part.startswith("after-round=")), None)
    if not learner_id or factor_text is None or round_text is None:
        raise argparse.ArgumentTypeError("expected learner-id:factor=X:after-round=N")
    return SlowLearnerAction(
        learner_id=learner_id,
        factor=float(factor_text.split("=", 1)[1]),
        after_round=int(round_text.split("=", 1)[1]),
    )

