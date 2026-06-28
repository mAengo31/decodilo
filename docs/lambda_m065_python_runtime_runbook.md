# Lambda M065 Python Runtime Runbook

M065 is the proposed supervised follow-up after M064. It may run only after fresh
operator approval and the usual one-shot execution gates.

Future M065 shape:

- launch at most one approved Lambda instance,
- wait for host and SSH readiness,
- execute exactly `python3 --version`,
- capture bounded stdout/stderr with redaction,
- do not run inline Python, scripts, imports, package managers, shell wrappers,
  command chaining, file transfer, port forwarding, setup scripts, cloud-init, or
  training,
- terminate the owned instance in the same supervised run,
- verify termination through Lambda read-only discovery/list/get.

The M064 runbook preview is non-executable and keeps `launch_ready=false` and
`launch_allowed=false`.
