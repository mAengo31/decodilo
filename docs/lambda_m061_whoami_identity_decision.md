# Lambda M061 Whoami Identity Decision

M060 may produce a future-only M061 decision after the M059 hostname closeout
succeeds.

The only passing next-step decision is:

- `plan_whoami_identity_command_review`

This means a future milestone may review a supervised `whoami` identity-command
run. It does not authorize immediate launch, immediate SSH, or immediate command
execution.

Still forbidden after M060:

- arbitrary remote commands
- interactive shell
- command chaining
- `nvidia-smi`
- remote Python
- file transfer
- port forwarding
- package installation
- setup scripts or cloud-init
- training

M061 must require fresh operator approval, one-shot arming, exactly one launch
attempt, exactly one reviewed command, owned termination, and read-only
termination verification.
