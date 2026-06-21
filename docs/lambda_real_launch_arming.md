# Lambda Real Launch Arming

M029 arming is a one-run token, not a general launch enablement.

Arming requires:
- M028 decision status `authorized_for_m029_one_instance_launch_attempt`.
- M029 authorization package.
- final budget/resource/window/operator evidence.
- emergency-stop evidence.
- idempotency key.
- `--execute-real-launch`.
- exact billable-action and terminate-required confirmation strings.

The token authorizes only:
- `launch_one_instance`.
- read-only instance verification.
- `terminate_owned_instance`.
- read-only termination verification.

It does not authorize restart, create/delete operations, SSH, setup scripts,
training, background execution, or unowned termination.
