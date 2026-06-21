# Lambda Remote Command Prohibition

M053 SSH-connectivity-only planning requires an empty remote command surface.
No interactive shell, TTY, stdin, command string, `nvidia-smi`, remote Python,
shell command, setup script, install command, or training command is allowed.

Future M054 may only review a bounded SSH handshake/authentication check unless
a later milestone creates a separate, explicit command-execution policy.
