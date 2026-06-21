# Lambda Minimal Terminate Request

The M027 terminate request model is limited to fake owned resources. It exists
to rehearse the future `terminate_owned_instance` boundary against local fake
state.

Required fields include:
- owned fake instance ID
- idempotency key
- resource scope hash
- ledger hash
- termination verification policy hash

The owned instance ID must be synthetic, such as `fake-i-*`, or an explicit
review placeholder. Live discovered Lambda resource IDs cannot be used as owned
fake-created resources.

Termination execution is fake-server-only. M027 does not implement real
termination, does not generate executable terminate commands, and does not
enable launch.

