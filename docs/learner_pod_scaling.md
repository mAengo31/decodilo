# Learner Pod Scaling

Milestone 014A adds a local-only planning layer for Decoupled DiLoCo learner pods.
It does not launch pods, call cloud APIs, or require GPUs.

The model supports three planning modes:

- `fixed_total_compute`: split a fixed GPU budget across more learner pods.
- `expanding_compute`: adding learners also adds compute.
- `scavenged_compute`: temporary or discounted learners may join and leave.

More learners can improve quorum availability when failures are independent, but the
benefit is not unlimited. Artifact writes, global update reads, syncer merge bandwidth,
checkpointing, replay, and algorithmic staleness can dominate once the learner count is
too high.

Use:

```bash
python -m decodilo.cli scaling learner-sweep \
  --mode fixed_total_compute \
  --total-gpus 64 \
  --candidate-learners 1,2,4,8,16 \
  --per-gpu-token-rate 1000 \
  --failure-rate-per-hour 0.02 \
  --recovery-time-seconds 300 \
  --training-duration-hours 24 \
  --model-params 7000000000 \
  --bytes-per-param 2 \
  --fragment-count 128 \
  --chunk-size-mb 64 \
  --sync-interval-steps 500 \
  --local-step-seconds 1.0 \
  --bandwidth-cap-gbps 10 \
  --artifact-read-gbps 20 \
  --artifact-write-gbps 10 \
  --syncer-merge-gbps 5 \
  --out /tmp/decodilo-learner-sweep.json
```

The output is a decision report with `launch_ready=false` and `launch_allowed=false`.

