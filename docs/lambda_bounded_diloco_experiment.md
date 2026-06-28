# Bounded Synthetic DiLoCo Experiment

`dev bounded-diloco-experiment` is the first complete local/offline bounded
synthetic DiLoCo experiment command. It composes the prior scaffold layers into
one deterministic artifact:

```bash
python -m decodilo.cli dev bounded-diloco-experiment \
  --synthetic \
  --learners 1 \
  --sync-rounds 1 \
  --fragments 2 \
  --inner-optimizer adamw \
  --outer-optimizer nesterov \
  --max-steps 1 \
  --out /tmp/decodilo-bounded-diloco-experiment.json
```

The command uses tiny deterministic in-memory vector state only. It performs no
network access, package installation, data/model download, real model training,
torch work, GPU work, background process, Lambda call, SSH, upload, or remote
command.

The report may state `optimization_fidelity=bounded_synthetic_diloco_experiment`
only when protocol, optimizer, fragment, integration, replay/metric, and
reference checks pass. It must keep `parameter_fragment_semantics` to
`synthetic_vector_fragments` unless true model/tensor fragment synchronization is
implemented.

The command must not claim paper-scale DiLoCo, real model training, true
model/layer fragmentation, communication/computation overlap, or quantized
communication.
