# Lambda M029 First Real Launch

M029 is the first milestone that may attempt a billable Lambda Cloud operation.
The scope is exactly one instance, followed by termination of that exact owned
instance in the same operator-supervised run.

Allowed operations:
- read-only discovery/list/get.
- launch exactly one instance.
- read-only verification of the owned instance.
- terminate exactly the owned instance.
- read-only verification that the owned instance is terminal or absent.

Forbidden operations:
- restart.
- create or delete SSH keys.
- create or delete filesystems.
- terminate unowned instances.
- launch more than one instance.
- SSH, setup scripts, cloud-init, or training workload.

The command must pass all M029 gates before any launch request is sent. If a
launch request succeeds or may have succeeded, termination verification is
mandatory.

M029D response-loss rule: if a launch request is sent and the response is lost,
the incident remains open until read-only discovery evidence, owned-instance
reconciliation, and manual Lambda console confirmation close it. A second launch
attempt is blocked while that incident remains open or unresolved.

M032 response-loss mitigation requires response capture, endpoint spec
verification, offline response-loss regression fixtures, and hold release for
future review before another launch review can proceed.

M034A gate rule: after M033, any future third launch attempt must pass explicit
M033/M034 artifact flags into `lambda m029 run`. The run path must load the
endpoint confirmation, response-capture lock, launch timeout policy, risk review,
correlation plan, reconciliation plan, M034 authorization, third go/no-go, and
M033 report before request construction.

Required third-attempt controls:
- launch timeout policy must set `launch_request_timeout_seconds >= 30`.
- `no_auto_launch_retry=true`.
- response capture must record HTTP status and redacted response metadata before
  parsing.
- the launch idempotency key must come from the third-attempt correlation plan.
- response-loss reconciliation may terminate only exact or high-confidence owned
  candidates.
- missing or invalid M033/M034 artifacts block the launch path.

The M034A gate and report remain non-launching and keep `launch_ready=false` and
`launch_allowed=false`.
## M030 Second-Attempt Review

After the M029C response-loss incident, no further launch attempt is considered
until the M029E closeout is present and M030 response-loss mitigation,
correlation, and reconciliation reviews pass. M030 remains review-only and does
not launch or terminate.
