# Lambda M029 Launch Authorization

The M029 authorization package is a one-time, next-milestone-only authorization
for exactly one future Lambda instance launch attempt.

Allowed future operations:
- `launch_one_instance`
- read-only instance verification
- `terminate_owned_instance`
- read-only termination verification

Forbidden operations:
- restart
- SSH key create/delete
- filesystem create/delete
- multi-instance launch
- SSH
- setup scripts
- training workloads

The authorization does not authorize launch now. M028 still reports
`launch_authorized_now=false`, `launch_ready=false`, and `launch_allowed=false`.

M029 consumes this package as one input to the arming token. The package still
does not permit restart, create/delete, SSH, setup scripts, training, or
unowned termination.
