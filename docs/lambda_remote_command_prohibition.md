# Lambda Remote Command Prohibition

M053 SSH-connectivity-only planning requires an empty remote command surface.
No interactive shell, TTY, stdin, command string, `nvidia-smi`, remote Python,
shell command, setup script, install command, or training command is allowed in
that planning layer.

Future M054 may only review a bounded SSH handshake/authentication check unless
a later milestone creates a separate, explicit command-execution policy.

M057 was that separate, explicit policy for exactly one no-op command: `true`.
M058 closes it out offline and opens only a future M059 identity-command review,
currently limited to `hostname`. Shell exploration, command composition, GPU
inspection, Python inspection, package installation, file transfer, port
forwarding, and training remain forbidden.
