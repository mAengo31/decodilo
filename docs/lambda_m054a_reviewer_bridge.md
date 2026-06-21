# Lambda M054A Reviewer Bridge

The M054A reviewer bridge is the only artifact that may expose future one-shot
permission fields for M054B:

- `one_shot_request_send_permitted=true`
- `one_shot_ssh_connectivity_probe_permitted=true`
- `max_launch_attempts=1`
- `max_ssh_connectivity_attempts=1`

Standing launch flags remain false. The bridge is valid only when authorization,
static validation, one-shot arming, and no-exec controls pass. M054A does not execute
the bridge.
