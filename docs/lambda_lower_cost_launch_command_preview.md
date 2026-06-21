# Lambda Lower-Cost Launch Command Preview

M038 produces a non-executable command preview for a future M039 launch review.
The preview is documentation and audit evidence only.

The preview includes `.env`, `LAMBDA_API_KEY`, M039 authorization, all
lower-cost M039 execution artifacts, response-loss controls, workdir
`/tmp/decodilo-lambda-m039`, and future operator-confirmation strings.

The future M039 run command must use the lower-cost flags on `lambda m029 run`:

```bash
python -m decodilo.cli lambda m029 run \
  --env-file .env \
  --env-key LAMBDA_API_KEY \
  --m039-authorization /tmp/decodilo-lambda-m039-authorization.json \
  --lower-cost-canonical-readiness /tmp/decodilo-lambda-lower-cost-canonical-readiness.json \
  --lower-cost-state-snapshot /tmp/decodilo-lambda-lower-cost-state-snapshot.json \
  --lower-cost-budget-lock /tmp/decodilo-lambda-lower-cost-budget-lock.json \
  --lower-cost-resource-lock /tmp/decodilo-lambda-lower-cost-resource-lock.json \
  --lower-cost-launch-window-lock /tmp/decodilo-lambda-lower-cost-launch-window-lock.json \
  --lower-cost-launch-plan /tmp/decodilo-lambda-strand-lower-cost-plan.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --lower-cost-gate-check /tmp/decodilo-lambda-lower-cost-gate-check.json \
  --m038a-report /tmp/decodilo-lambda-m038a-report.json \
  --workdir /tmp/decodilo-lambda-m039 \
  --execute-real-launch \
  --confirm-billable-action "I understand this may create a billable Lambda instance and must be terminated" \
  --confirm-terminate-required "I understand this run must terminate the owned instance and verify termination"
```

The preview always has `executable=false`, `launch_ready=false`, and
`launch_allowed=false`.

After M038A approval, the preview status may become `ready_for_future_m039`.
That means the audit package is ready for a later supervised M039 launch review;
it does not make the command executable. The preview records only the selected
SSH key hash and response-loss control artifact path, not private key material.
The raw existing SSH key name is read only from the local private selection
artifact during request construction and is redacted from persisted public
reports.
