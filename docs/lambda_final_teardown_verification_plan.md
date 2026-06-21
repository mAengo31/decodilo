# Lambda Final Teardown Verification Plan

M028 finalizes the future M029 teardown verification plan.

The plan requires:
- owned instance ID recorded from launch response or read-only reconciliation
- termination only for the owned instance
- read-only list/get verification until terminal or absent state
- timeout escalation to manual review
- final ledger and read-only audit collection
- billable-action evidence collection

OS shutdown is explicitly insufficient. M028 does not include executable
terminate commands.

M029 is the first milestone that may execute the owned-instance termination
step. Verification must still use Lambda read-only get/list; OS shutdown is not
accepted as termination.
