# Lambda Capacity-Selected Operator Approval

M045 records the operator decision for the candidate selected by the
capacity-history-aware flexible selector. The accepted candidate for this
review is `gpu_8x_a100_80gb_sxm4`.

Approval requires acknowledgements that:

- the selected candidate is `gpu_8x_a100_80gb_sxm4`
- the candidate is larger than needed for lifecycle smoke
- the candidate is catalog-backed unless fresh live availability proves
  otherwise
- `gpu_1x_h100_pcie` was excluded because it recently failed due to capacity
- a future M046 attempt may still return a capacity error
- no automatic launch retry is allowed
- only one instance may be attempted
- the budget is `$50` and runtime is 30 minutes
- an existing SSH key will be attached, but no SSH will be used
- no setup scripts, cloud-init, training, restart, create, or delete operations
  will run
- owned-instance termination is required if an instance is created
- termination must be verified through read-only Lambda discovery/list/get
- OS shutdown is not sufficient termination
- the approval is for future review only, not immediate launch

Decline paths are `declined_wait_for_live_availability` and
`declined_manual_candidate_selection`. All paths keep `launch_ready=false` and
`launch_allowed=false`.
