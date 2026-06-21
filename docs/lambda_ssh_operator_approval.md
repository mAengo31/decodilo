# Lambda SSH Operator Approval

M050 supports three future-only SSH approval states:

- `declined_no_ssh`
- `approved_ssh_connectivity_check_only`
- `approved_single_allowlisted_command`

The default M050 path declines SSH. Approval does not authorize immediate
execution; it only allows a future M051 review package to be built.

Interactive shells, setup scripts, package installation, training, background
processes, and broad command execution are explicitly forbidden.

M053 introduces a separate M054 SSH-connectivity-only approval model. That model
can approve only a future review and still forbids immediate SSH, launch, remote
commands, file transfer, port forwarding, package installation, and training.
