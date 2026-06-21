# Lambda SSH Connectivity Scope

M053 defines a future M054 SSH-connectivity-only review. M053 does not launch,
SSH, open sockets to instances, use credentials, or call live Lambda APIs.

Allowed future modes are limited to:

- `ssh_connectivity_handshake_only`
- `ssh_auth_check_only`

Forbidden actions remain:

- interactive shell
- remote command execution
- file transfer
- port forwarding
- package installation
- setup scripts or cloud-init
- training
- background or unattended execution

Any future M054 attempt must launch at most one instance, terminate exactly the
owned instance if created, and verify termination through Lambda read-only
discovery/list/get.

## M054A execution-package scope

M054A narrows the future M054B execution package to one lifecycle launch plus one
bounded SSH connectivity/authentication probe. The probe is still not executed in
M054A.

The future probe must not request an interactive shell, must not include a remote
command, and must not transfer files or open port forwards. Package installation,
setup scripts, cloud-init, and training remain out of scope.

M054A artifacts are planning and reviewer artifacts only. They must keep
`launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false`.
