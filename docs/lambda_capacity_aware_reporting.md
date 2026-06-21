# Lambda Capacity-Aware Reporting

Generic launch reports can mark failed mutation attempts as requiring manual
review. Capacity-aware reporting adds a narrower teardown semantic.

If a launch response has:

- HTTP 400
- JSON error body
- provider message classified as insufficient capacity
- no owned instance ID
- final discovery count 0
- final unmanaged count 0

then the refined launch outcome is:

- `launch_outcome=capacity_rejected_no_instance_created`
- `termination_required=false`
- `ownership_uncertain=false`
- `manual_review_required_for_teardown=false`

This does not rewrite historical artifacts. It gives later reports a clearer
field for distinguishing "capacity rejected, no instance created" from
"ownership or teardown still needs manual review."

