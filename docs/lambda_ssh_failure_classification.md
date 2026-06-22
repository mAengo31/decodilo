# Lambda SSH Failure Classification

M055B classifies SSH connectivity probe failures offline. It does not launch, call
Lambda, open sockets, SSH, or use credentials.

The classifier uses redacted stderr, exit code, and TCP readiness evidence. Historical
M055 evidence had exit status 255 but no stderr, so it remains
`unknown_exit_255`. Future live attempts should capture bounded redacted stderr so
that failures such as `permission_denied_publickey`, host-key verification failure,
identity-file issues, or key-permission errors can be separated.

All classifier artifacts keep `launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false`.
