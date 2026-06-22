# Lambda SSH Capacity Retry Closeout

M055D closes the M055C SSH diagnostic attempt as a provider capacity rejection
with no instance created. It does not launch, terminate, call Lambda, use
credentials, SSH, or spend money.

The closeout succeeds only when the launch request was sent, Lambda returned a
capacity-class 400 JSON response, no owned instance ID exists, SSH was not
attempted, and final read-only discovery shows zero visible and unmanaged
instances.

Generic `manual_review_required` from the run report is refined to
`teardown_not_required_capacity_rejected` only for this exact no-instance
capacity outcome. The same candidate/region is blocked for future retry unless
fresh live availability evidence or an explicit future review changes the gate.
