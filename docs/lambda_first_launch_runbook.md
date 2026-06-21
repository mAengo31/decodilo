# Lambda First Launch Runbook

The M025 first-launch runbook is non-executable. It records the future
operator flow for a one-instance, 30-minute, 50 USD maximum first launch review.

It includes preconditions, operator presence, secret handling, budget lock,
launch window, placeholder future commands, post-launch read-only verification,
runtime timer, mandatory termination, termination verification, escalation,
artifact collection, post-run audit, and cleanup.

The runbook explicitly forbids training workloads, SSH, setup scripts,
multi-instance launch, unattended launch, and production use. Placeholder
commands are marked `non_executable=true`.

M028 keeps the runbook non-executable while adding final budget,
launch-window, operator, and teardown-verification locks for the future M029
review.
