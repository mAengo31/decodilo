# Lambda Catalog Availability Risk Acceptance

M041 records an explicit operator decision for catalog-only Lambda availability
evidence. It does not launch, terminate, mutate resources, or spend money.

Accepted risk requires every acknowledgement:

- live availability is not proven
- the selected candidate is catalog-backed, not live-available
- the previous `gpu_1x_h100_pcie` attempt failed due to capacity
- M042 may receive another capacity error
- no automatic launch retry is allowed
- exactly one instance may be attempted
- maximum budget is $50
- maximum runtime is 30 minutes
- an existing SSH key is attached, but no SSH is used
- no setup scripts, cloud-init, or training run
- owned-instance termination is required if an instance is created
- termination must be verified through read-only Lambda list/get discovery
- OS shutdown is not sufficient termination

Accepted status is future-only:
`accepted_for_future_m042_review`. It never sets `launch_ready` or
`launch_allowed`.

Declined risk records `declined_wait_for_live_availability` and should produce a
wait-for-live-availability plan instead of an M042 authorization package.
