# Lambda M055 Host Discovery Fix

M055 adds a provider-metadata host discovery layer for SSH-connectivity-only runs.

The host discovery helper searches conservative provider metadata shapes, including
flat fields such as `public_ip`, `ip_address`, `hostname`, and nested fields such as
`network.public_ip`, `network_interfaces[*].public_ip`, and
`network.interfaces[*].public_ip`.

The helper returns structured status:

- `FOUND`
- `NOT_FOUND`
- `AMBIGUOUS`
- `INVALID`

Private or non-global IPs are rejected by default. `LAMBDA_ALLOW_PRIVATE_SSH_HOST=true`
is required before a private IP may be considered. `LAMBDA_SSH_HOST_OVERRIDE` is an
explicit operator fallback only; it is never used silently.

Public reports store redacted host values and sanitized metadata key names/paths. Raw
private key material is never serialized. Missing keys are reported as `ssh_key_missing`,
not as host discovery failure.

For M055-compatible real runs, `CONFIRM_LAMBDA_BILLABLE_ACTION=true` is required in
addition to the existing exact command confirmations. A run may launch at most one
instance, perform at most one bounded SSH connectivity/authentication probe, and must
terminate exactly the owned instance.

M055 still forbids remote shell commands, command output collection, file transfer, port
forwarding, package installation, setup scripts, cloud-init, and training.
