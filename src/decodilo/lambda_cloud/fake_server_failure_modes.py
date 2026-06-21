"""Deterministic fake failure modes for M027 minimal mutation tests."""

from __future__ import annotations

from typing import Literal

LambdaMinimalFakeFailureMode = Literal[
    "none",
    "launch_response_lost",
    "launch_timeout_but_created",
    "terminate_response_lost",
    "terminate_timeout_but_terminated",
    "malformed_launch_response",
    "malformed_terminate_response",
]


class LambdaMinimalFakeFailure(Exception):
    def __init__(self, mode: LambdaMinimalFakeFailureMode, message: str) -> None:
        super().__init__(message)
        self.mode = mode
