# Lambda Strand CLI Compatibility

M036R records compatibility evidence from the Strand-AI `lambda-cli`:
https://github.com/Strand-AI/lambda-cli

The Strand CLI is unofficial and is not affiliated with or endorsed by Lambda.
This repository treats it as behavioral evidence only because the operator has
tested it successfully. It is not support confirmation and it does not authorize
execution.

Compatibility shape:

- API base URL: `https://cloud.lambdalabs.com/api/v1`
- Timeout: 30 seconds
- Auth: `Authorization: Bearer <api_key>`
- List instance types: `GET /instance-types`
- List running instances: `GET /instances`
- Get instance: `GET /instances/{instance_id}`
- Launch: `POST /instance-operations/launch`
- Terminate: `POST /instance-operations/terminate`

M036R commands are offline and no-mutation:

```bash
python -m decodilo.cli lambda strand-cli compatibility \
  --out /tmp/decodilo-lambda-strand-compatibility.json

python -m decodilo.cli lambda strand-cli gap-analysis \
  --out /tmp/decodilo-lambda-strand-gap-analysis.json

python -m decodilo.cli lambda strand-cli migration-plan \
  --gap-analysis /tmp/decodilo-lambda-strand-gap-analysis.json \
  --out /tmp/decodilo-lambda-strand-migration-plan.json
```

All reports keep `launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false`.

M037R uses this same compatibility profile to build a future-review
`gpu_1x_h100_pcie` plan. The lower-cost plan still treats Strand as unofficial
behavioral evidence and requires an existing SSH key name before any future
launch review can proceed.
