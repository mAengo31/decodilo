# Lambda Wait For Live Availability

If the operator declines catalog-only availability risk, M041 produces a wait
plan. The plan authorizes no launch and no mutation.

Allowed follow-up work is limited to read-only discovery when the operator asks
for another availability check. Product catalog data remains catalog evidence
only until a live endpoint provides useful availability evidence or the operator
later accepts catalog-only risk in a separate review.

The wait plan keeps:

- `launch_ready=false`
- `launch_allowed=false`
- `billable_action_performed=false`
- `real_mutation_enabled=false`
