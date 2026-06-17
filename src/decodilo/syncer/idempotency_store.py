"""Typed idempotency records for learner fragment submissions."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from decodilo.errors import InvariantViolation

IDEMPOTENCY_SCHEMA_VERSION = "v1"
IdempotencyDecision = Literal[
    "accepted",
    "rejected",
    "duplicate",
    "expired_duplicate",
]


class IdempotencyRecord(BaseModel):
    """A durable decision for one idempotent fragment submission."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    idempotency_key: str
    learner_id: str
    fragment_id: str
    first_seen_global_version: int = Field(ge=0)
    last_seen_global_version: int = Field(ge=0)
    round_id: str | None = None
    decision: IdempotencyDecision
    rejection_reason: str | None = None
    artifact_ref_hash: str | None = None
    payload_checksum: str | None = None
    token_count: int = Field(ge=0)
    useful_tokens_counted: bool
    created_logical_time: int = Field(ge=0)
    last_seen_logical_time: int = Field(ge=0)
    expires_after_global_version: int | None = Field(default=None, ge=0)
    compacted: bool = False
    schema_version: str = IDEMPOTENCY_SCHEMA_VERSION

    @field_validator("schema_version")
    @classmethod
    def _known_schema(cls, value: str) -> str:
        if value != IDEMPOTENCY_SCHEMA_VERSION:
            raise ValueError(f"unknown idempotency schema {value!r}")
        return value


class IdempotencyStore(BaseModel):
    """Serializable idempotency table with expired-key tombstones."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    records: dict[str, IdempotencyRecord] = Field(default_factory=dict)
    expired_keys: dict[str, IdempotencyRecord] = Field(default_factory=dict)
    compacted_through_global_version: int = 0
    compacted_through_logical_time: int = 0
    schema_version: str = IDEMPOTENCY_SCHEMA_VERSION

    @field_validator("schema_version")
    @classmethod
    def _known_schema(cls, value: str) -> str:
        if value != IDEMPOTENCY_SCHEMA_VERSION:
            raise ValueError(f"unknown idempotency store schema {value!r}")
        return value

    @property
    def record_count(self) -> int:
        return len(self.records)

    def put(self, record: IdempotencyRecord) -> IdempotencyStore:
        if record.run_id != self.run_id:
            raise InvariantViolation("idempotency record run_id mismatch")
        records = dict(self.records)
        records[record.idempotency_key] = record
        expired = dict(self.expired_keys)
        expired.pop(record.idempotency_key, None)
        return self.model_copy(update={"records": records, "expired_keys": expired})

    def get(self, key: str) -> IdempotencyRecord | None:
        return self.records.get(key)

    def duplicate_decision(
        self,
        key: str,
        *,
        logical_time: int,
        global_version: int,
    ) -> IdempotencyRecord:
        existing = self.records.get(key)
        if existing is None:
            expired = self.expired_keys.get(key)
            if expired is not None:
                return expired.model_copy(
                    update={
                        "decision": "expired_duplicate",
                        "last_seen_logical_time": logical_time,
                        "last_seen_global_version": global_version,
                    }
                )
            raise KeyError(key)
        return existing.model_copy(
            update={
                "decision": "duplicate",
                "last_seen_logical_time": logical_time,
                "last_seen_global_version": global_version,
            }
        )

    def expire(self, key: str, *, compacted: bool = True) -> IdempotencyStore:
        record = self.records.get(key)
        if record is None:
            return self
        records = dict(self.records)
        records.pop(key)
        expired = dict(self.expired_keys)
        expired[key] = record.model_copy(update={"compacted": compacted})
        return self.model_copy(update={"records": records, "expired_keys": expired})

    def stable_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def to_checkpoint_payload(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_checkpoint_payload(cls, payload: dict) -> IdempotencyStore:
        return cls.model_validate(payload)

