# Lambda M027 Authorization Record

The M027 authorization record translates an approved M026 decision into the
allowed scope for the next milestone.

Allowed M027 scope:
- implement minimal `launch_one_instance` request code disabled by default
- implement minimal `terminate_owned_instance` request code disabled by default
- integrate endpoint policy, arming gate, budget lock, idempotency, resource
  ledger, and termination verification
- test only against fake servers and fixtures

Forbidden scope:
- real launch execution
- real termination execution
- restart
- SSH-key or filesystem create/delete
- multi-instance launch
- SSH, setup scripts, or training

The record cannot enable real mutation or launch.
