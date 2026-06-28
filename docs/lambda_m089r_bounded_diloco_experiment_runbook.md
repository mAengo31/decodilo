# M089R Bounded Synthetic DiLoCo Experiment Runbook Preview

M089R is a future supervised remote run. This document is non-executable and
does not authorize launch.

The only approved experiment command shape is:

```bash
env PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src \
  python3 -m decodilo.cli dev bounded-diloco-experiment \
  --synthetic \
  --learners 1 \
  --sync-rounds 1 \
  --fragments 2 \
  --inner-optimizer adamw \
  --outer-optimizer nesterov \
  --max-steps 1 \
  --out /tmp/decodilo-bounded-diloco-experiment.json
```

The declared artifact path is `/tmp/decodilo-bounded-diloco-experiment.json`.

Any future live run must rebuild and validate a fresh source bundle, validate
the local dependency wheelhouse bundle, validate an 11-stage manifest, run fresh
read-only discovery, pass plan/gate and one-shot arming, and receive explicit
operator approval.

The run must use local-only dependency installation, exactly one experiment
command, bounded stdout/stderr capture, declared-artifact capture on success or
failure, owned-instance termination, and read-only termination verification.

It must not perform dataset download, model download, real training, benchmark,
stress test, internet package installation, arbitrary shell access, command
chaining, background processes, arbitrary file reads, port forwarding, or extra
file transfer.
