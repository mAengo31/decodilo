# Lambda Lower-Cost Launch Gate

M038 converts the M037R lower-cost Strand-compatible review into a future M039
gate package. It remains no-launch, no-termination, no-mutation, and no-spend.

The gate requires fresh read-only discovery, existing SSH key selection,
canonical readiness for `gpu_1x_h100_pcie`, budget/resource/window locks,
response-loss controls, and explicit operator approval before future M039 can be
authorized.

If only the operator approval template exists, the M039 authorization remains
`not_authorized` and the gate remains blocked. Launch flags stay false.

M038A records explicit operator approval for a future lower-cost M039 review.
When the approval, authorization, readiness, and response-loss controls pass,
the gate can report `gate_passed=true` while still keeping
`launch_ready=false` and `launch_allowed=false`. M039 remains the separate
billable milestone.

M039A adds the execution gate used by `lambda m029 run` when lower-cost flags
are present:

```bash
python -m decodilo.cli lambda lower-cost execution-gate-check \
  --m039-authorization /tmp/decodilo-lambda-m039-authorization.json \
  --canonical-readiness /tmp/decodilo-lambda-lower-cost-canonical-readiness.json \
  --state-snapshot /tmp/decodilo-lambda-lower-cost-state-snapshot.json \
  --budget-lock /tmp/decodilo-lambda-lower-cost-budget-lock.json \
  --resource-lock /tmp/decodilo-lambda-lower-cost-resource-lock.json \
  --launch-window-lock /tmp/decodilo-lambda-lower-cost-launch-window-lock.json \
  --launch-plan /tmp/decodilo-lambda-strand-lower-cost-plan.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-lower-cost-execution-gate-check.json
```

If any lower-cost M039 flag is present on `lambda m029 run`, every lower-cost
artifact is required and the old M028/M029 resource path must not be used. The
execution gate proves `gpu_1x_h100_pcie`, `us-west-1`, `quantity=1`, an
existing private SSH key name for request construction, response capture, a
30 second timeout, and no automatic launch retry before request construction.

M040 adds a capacity-error closeout path for structured 400 responses such as
`Not enough capacity to fulfill launch request.` When final read-only discovery
shows zero visible/unmanaged instances, this closes as no instance created. A
same-shape retry remains blocked unless a future milestone has fresh
availability evidence and explicit operator risk acceptance. Lifecycle smoke
follow-up should use the availability-first selector.
