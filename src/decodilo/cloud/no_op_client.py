"""No-op cloud client for dry-run tests."""

from __future__ import annotations


class NoOpCloudClient:
    """Client that records no API calls and cannot launch anything."""

    def __init__(self) -> None:
        self.api_calls_attempted = 0

    def launch(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        self.api_calls_attempted += 1
        raise RuntimeError("NoOpCloudClient cannot launch resources")
