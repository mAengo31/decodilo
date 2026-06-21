# Remote Backend Requirements

Milestone 015 defines requirements for a future remote artifact backend without
implementing one.

The requirement set is generated from a learner-scaling report because the
backend must be designed around expected learner count, stress learner count,
artifact read/write bandwidth, artifact operations, syncer merge throughput,
checkpoint growth, event-log growth, and replay snapshot frequency.

```bash
python -m decodilo.cli remote requirements \
  --scaling-report /tmp/decodilo-pod-optimization.json \
  --out /tmp/decodilo-remote-requirements.json
```

The output includes throughput, latency, consistency, integrity, security,
lifecycle, cost, replay, and checkpoint requirements. It remains planning-only:
no remote backend is enabled.

## Milestone 016

The requirement set now feeds the readiness gate, conformance suite, evidence
package, and manual provider matrix. A simulator pass still does not permit SDK
addition, credential use, or remote backend enablement.
