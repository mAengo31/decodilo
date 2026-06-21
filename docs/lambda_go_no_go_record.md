# Lambda Go/No-Go Record

The M025 go/no-go record summarizes the final prelaunch review outcome.

Allowed statuses:
- `no_go`
- `blocked`
- `go_for_future_m026_real_launch_review`

Forbidden outcomes include launch approval, launch allowed, and real mutation
enabled. A clean M025 record can only nominate the evidence for a future M026
real-launch review. It cannot approve or execute launch.

M026 may consume this record as evidence. Even when the M026 decision approves
M027 minimal mutation implementation work, that approval remains code-only and
disabled by default.

M028 may consume the later evidence chain to authorize only a future M029
one-instance launch attempt. It does not convert any go/no-go record into
current-build launch permission.
