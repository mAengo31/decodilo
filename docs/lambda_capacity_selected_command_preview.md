# Lambda Capacity-Selected Command Preview

The M045 command preview is non-executable and intended only to show the shape
of a future M046 supervised command.

The preview must include:

- M046 authorization artifact
- capacity-selected cost/risk review
- capacity-selected operator approval
- capacity-selected gate check
- capacity-aware selector output
- capacity-aware selector authorization
- capacity-aware selector gate check
- capacity history and retry policy
- response-loss controls
- SSH key selection
- M045 report
- future workdir `/tmp/decodilo-lambda-m046`

The future command must use the M046 capacity-selected flags on
`lambda m029 run`:

- `--capacity-selected-m046-authorization`
- `--capacity-selected-cost-risk-review`
- `--capacity-selected-operator-approval`
- `--capacity-selected-gate-check`
- `--capacity-aware-selector-output`
- `--capacity-aware-selector-authorization`
- `--capacity-aware-selector-gate-check`
- `--capacity-history`
- `--capacity-retry-policy`
- `--ssh-key-selection`
- `--response-loss-controls`
- `--m045-report`

The preview must not include raw SSH key names and must keep
`executable=false`, `launch_ready=false`, and `launch_allowed=false`.
