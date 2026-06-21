# Lambda Catalog Rotation Risk Acceptance

Catalog rotation risk acceptance is required before the selected
`gpu_8x_a100_80gb_sxm4` candidate can move to a future M045 launch review.

Acceptance requires acknowledgements that live availability is not proven, the
candidate is catalog-backed, the prior H100 PCIe shape failed for capacity, the
A100 shape is larger than lifecycle-smoke minimum, another capacity error may
occur, no automatic retry is allowed, only one instance may be attempted, the
budget/runtime limits remain $50 and 30 minutes, an existing SSH key may be
attached without SSH usage, no setup/cloud-init/training will run, and any owned
instance must be terminated and verified through read-only Lambda discovery.

The accepted status is
`accepted_gpu_8x_a100_80gb_sxm4_for_future_review`. It is future-review only and
does not enable launch.
