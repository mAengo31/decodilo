# Lambda Second Attempt Authorization

M030 authorization can only produce
`authorized_for_future_m031_second_launch_attempt`.

It cannot produce launch approval, launch readiness, launch permission, real
mutation enablement, or execute-now semantics. It is review evidence for a
future milestone only.

Authorization requires:

- closed M029C incident evidence
- passed risk review
- passed response-loss mitigation review
- correlation plan
- reconciliation plan

Forbidden scope remains restart, create/delete resources, SSH, setup scripts,
training, background execution, and any current-milestone mutation.
