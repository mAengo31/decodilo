# Lambda Strand Lower-Cost Launch Plan

M037R builds a future-review launch plan for `gpu_1x_h100_pcie` using the
operator-tested Strand-AI CLI payload shape. The Strand CLI remains unofficial
behavioral evidence, not Lambda support confirmation.

The plan is review-only. It must include:

- `region_name`
- `instance_type_name=gpu_1x_h100_pcie`
- `ssh_key_names` containing at least one existing key name
- `quantity=1`

The plan forbids setup scripts, cloud-init/user data, SSH execution, training,
multi-node launch, restart, and create/delete resource operations.

```bash
python -m decodilo.cli lambda strand lower-cost-plan \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --region us-west-1 \
  --out /tmp/decodilo-lambda-strand-lower-cost-plan.json
```

The command does not launch. Reports keep `launch_ready=false` and
`launch_allowed=false`.

M038 consumes this plan as canonical lower-cost readiness input for future M039
review. M038 still cannot launch or mark launch allowed.

M039A wires this plan into `lambda m029 run` through the lower-cost artifact
flags. When those flags are present, request construction must use the
Strand-compatible payload:

```json
{
  "region_name": "us-west-1",
  "instance_type_name": "gpu_1x_h100_pcie",
  "ssh_key_names": ["<existing private key name>"],
  "quantity": 1
}
```

The old `gpu_8x_h100_sxm` M028/M029 path is not a fallback for lower-cost M039
execution.
