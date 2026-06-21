# Lambda Capacity Error Closeout

M040 classifies a lower-cost launch rejection as a capacity/availability
selection problem when the persisted launch response shows:

- `status_code=400`
- `classification=http_error_json`
- a redacted provider error message indicating unavailable capacity
- no owned instance ID
- post-run read-only discovery with zero visible and unmanaged instances

When those conditions hold, the incident closes as
`closed_capacity_unavailable_no_instance_created`. Termination is not required
because Lambda rejected the launch before returning an owned instance.

Same-shape retry remains blocked unless a future milestone has fresh
availability evidence and explicit operator risk acceptance. M040 never launches
or terminates resources.

M041 records that explicit risk decision. If the operator accepts catalog-only
availability risk, M041 may authorize only a future M042 review. If the operator
declines, M041 produces a wait-for-live-availability plan.

M043 adds repeated-capacity follow-up. When M039B and M042 both close as
`closed_capacity_unavailable_no_instance_created` for the same shape, same-shape
retry is blocked by default and catalog candidate rotation may be prepared for a
future review.
