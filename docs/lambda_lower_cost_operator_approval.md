# Lambda Lower-Cost Operator Approval

M038 can generate an operator approval template for a future M039 lower-cost
launch attempt. The template requires acknowledgements for possible billable
action, one instance only, $50 budget, 30 minute runtime, `gpu_1x_h100_pcie`,
existing SSH key attachment without SSH usage, no setup/cloud-init/training,
owned termination, read-only termination verification, no OS shutdown shortcut,
no automatic launch retry, and operator presence.

The template does not authorize immediate launch.

M038A can convert the template into
`approved_for_future_m039_lower_cost_launch_attempt` only when the operator
explicitly acknowledges every lower-cost launch constraint and passes the
future-only approval flag:

```bash
python -m decodilo.cli lambda lower-cost operator-approval-template \
  --approve-future-m039 \
  --acknowledge-all \
  --out /tmp/decodilo-lambda-lower-cost-operator-approval.json
```

This approval is still not an execution approval. It keeps
`launch_ready=false`, `launch_allowed=false`, and `real_mutation_enabled=false`.
The future M039 run must remain supervised and must re-check gates before any
billable request.
