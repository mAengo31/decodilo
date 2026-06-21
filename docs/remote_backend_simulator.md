# Remote Backend Simulator

The local remote-backend simulator stores data locally/in memory and models
remote-like behavior with logical time.

It can simulate read/write latency, bandwidth caps, operations-per-second caps,
transient and persistent failures, corrupt reads, delayed visibility, stale
lists, read-after-write consistency on or off, conditional put, object versioning
flags, delete lag, lifecycle delete, and idempotent retry behavior.

The simulator is deterministic from its configuration and seed. It makes no
network calls and is not a production backend.

```bash
python -m decodilo.cli remote simulate-backend \
  --requirements /tmp/decodilo-remote-requirements.json \
  --read-gbps 10 \
  --write-gbps 5 \
  --ops-per-second 1000 \
  --strong-consistency \
  --conditional-put \
  --object-versioning \
  --seed 123 \
  --out /tmp/decodilo-remote-sim.json
```

