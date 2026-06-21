# Remote Backend Preflight

Cloud preflight remains non-launchable and now checks for remote-backend design
evidence when a workdir is supplied.

Required evidence before a future backend can be considered:

- learner-scaling report
- backend design targets
- remote backend requirements file
- remote backend design validation report

Missing evidence produces warnings. Passing simulator evidence does not enable a
remote backend and does not make cloud launch ready.

Cloud preflight continues to report:

```json
{"launch_ready": false, "launch_allowed": false}
```

It also warns that no remote backend is implemented, simulator results are not
production proof, no credentials or real API integration exist, and no cloud
launch is enabled.

Milestone 016 adds readiness, conformance, evidence package, and provider matrix
summaries to preflight when those reports are present. Missing readiness
evidence remains a warning or blocker for future review, but cloud preflight
still reports `launch_ready=false` and `launch_allowed=false`.

Milestone 017 adds proposal, decision-record, SDK-guard, risk-register, and
review-package summaries. A `candidate_for_future_sdk_review` decision still
reports: future SDK review candidate only; backend remains disabled.
