# Lambda Fake Teardown Verification

M021 fake teardown operates only on synthetic fake resources created by the fake
lifecycle executor. It never terminates Lambda resources and never emits an
executable termination command.

Teardown transitions fake resources through:

```text
running/healthy -> terminate_requested -> terminating -> terminated
```

Repeated fake teardown is idempotent. Already terminated resources remain
terminated, and verification succeeds only when every fake resource is terminal.

Failure injection can leave a resource in `failed_terminate`, which sets
`manual_review_required=true` in the fake report and verification output.
That manual review is for the fake rehearsal state only; real cloud resources
are still read-only evidence and are not modified.

M022 adds a teardown audit that checks journal terminate events, terminal fake
states, failed terminate resources, and counter consistency. It never generates
real terminate commands.
