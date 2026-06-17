# Trainer Compatibility Matrix

Milestone 007 adds a trainer compatibility matrix so trainer adapters can be
checked against the runtime contract before they are used in local process
runs.

## Trainers

Required trainers:

- `numpy_convex`
- `scripted`

Optional trainers:

- `torch_tiny`
- `torch_causal_lm`

If torch is not installed, optional torch trainers are reported as unavailable
and skipped rather than failed.

## Contract Checks

The matrix checks:

- initialization
- `train_local_steps`
- nonnegative token counts
- state export
- fragment validation
- global update application
- checkpoint/restore checksum preservation
- state byte estimate
- health reporting
- optional evaluation when supported

The contract is not a full ML quality test. It verifies runtime compatibility:
state can move safely across process and syncer boundaries, tokens are
accounted explicitly, and future trainers can implement the same interface.

## CLI

List trainers:

```bash
python -m decodilo.cli trainer list
```

Check one trainer:

```bash
python -m decodilo.cli trainer check \
  --trainer numpy_convex \
  --workdir /tmp/decodilo-trainer-check
```

Run the matrix:

```bash
python -m decodilo.cli trainer matrix \
  --workdir /tmp/decodilo-trainer-matrix \
  --include-optional
```

The matrix writes `trainer_matrix.json` under the chosen workdir.

