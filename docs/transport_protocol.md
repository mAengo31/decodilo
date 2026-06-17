# Local Transport Protocol

Milestone 003 uses JSONL-over-TCP on localhost to create a real process boundary
without introducing external infrastructure. It is intentionally simple:

- one UTF-8 JSON object per line
- asyncio streams from the Python standard library
- localhost binding by default
- configurable message size limits
- request/response plus short long-poll behavior for learner update delivery

This is not the final production transport. It is a correctness harness for
process boundaries, idempotency, replay, heartbeat timeouts, and local failure
handling before any GPU, cloud, or WAN runtime exists.

## Envelope Schema

Every transport message is a `v1` envelope:

```json
{
  "schema_version": "v1",
  "message_id": "learner-0:...",
  "run_id": "run-...",
  "sender_id": "learner-0",
  "recipient_id": "syncer",
  "message_type": "submit_fragment",
  "idempotency_key": "run-...:learner-0:step-10:v-0",
  "payload": {},
  "created_logical_time": 12
}
```

Supported message types:

- `register_learner`
- `register_learner_ack`
- `heartbeat`
- `heartbeat_ack`
- `request_global_state`
- `global_state_response`
- `submit_fragment`
- `submit_fragment_ack`
- `submit_fragment_rejected`
- `sync_round_committed`
- `subscribe_updates`
- `subscribe_updates_ack`
- `global_update_available`
- `global_update_payload`
- `global_update_ack`
- `backpressure_warning`
- `backpressure_reject`
- `learner_shutdown`
- `syncer_shutdown`
- `error`

`event_id` is not a transport field. Event IDs are still assigned by the event
log path.

## Idempotency

`submit_fragment` requires an `idempotency_key`. The syncer stores the first
outcome for each key and treats later messages with the same key as duplicates.
Duplicates do not resubmit fragments, do not double-count tokens, and do not
apply deltas twice.

Duplicate transport messages are logged as transport lifecycle events so replay
remains deterministic and syncer state is not corrupted.

## Update Delivery

Learners send `subscribe_updates` with their last applied global version. If a
new version is available, the syncer returns `global_update_payload`; otherwise
it returns `subscribe_updates_ack` after a short timeout. Learners acknowledge
applied versions with `global_update_ack`.

This is still localhost-only and stdlib-only. It is stronger than arbitrary
polling, but it is not a final WAN-scale transport design.

## Backpressure

The runtime can reject excessive or oversized fragment submissions with
`backpressure_reject`. These rejections are idempotent, do not mutate global
state, and are accounted separately from stale fragment rejection.

## Size Limits

The default maximum message size is 1 MB. Oversized messages receive an `error`
envelope and do not crash the server.

## Localhost Default

The server binds to `127.0.0.1` by default. Tests use port `0` so the operating
system chooses an ephemeral local port. Binding to public interfaces is not used
by the local runner.
