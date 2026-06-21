# Lambda Termination Verification Policy

The termination verification policy is design-only in M023.

Future termination must record the owned instance ID before launch, terminate
only that owned instance ID, poll read-only list/get endpoints until the
instance is absent or terminal, reconcile the resource ledger, record final
status, fail on timeout, and require manual review for unknown state.

Operating-system shutdown is not sufficient evidence of cloud resource
termination. Unowned termination is forbidden. No real termination code exists
in M023.

M024 keeps this policy as evidence for the disabled skeleton only. The skeleton
can require the policy before preparing a review-only terminate plan, but it
still cannot construct or send a terminate request.

M025 adds a non-executable termination runbook around this policy. The runbook
keeps the same core rule: future termination must be verified through Lambda
read-only state, and OS shutdown is insufficient.

M029 implements this policy for the first owned-instance launch attempt:
terminate only the recorded owned instance ID, then verify terminal or absent
state through Lambda read-only get/list.
