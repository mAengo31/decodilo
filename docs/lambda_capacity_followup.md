# Lambda Capacity Follow-Up

M043 reviews the M039B and M042 lower-cost launch attempts after both returned
Lambda capacity errors.

The follow-up is review-only. It must not launch, terminate, create, delete,
SSH, run setup scripts, or spend.

Required evidence:

- capacity closeout for the latest attempt
- prior capacity closeout when available
- final read-only discovery when available
- non-sample price catalog
- existing SSH key selection

If the latest closeout has a 400 capacity error, no owned instance ID, and final
discovery shows zero visible and unmanaged instances, M043 records:

- `teardown_risk_status=no_teardown_required_no_instance_created`
- `termination_required=false`
- `same_fixed_shape_retry_blocked=true`

Repeated capacity errors for the same shape should move the strategy away from a
silent same-shape retry and toward either live availability evidence or a
future catalog candidate rotation review.

