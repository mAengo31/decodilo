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
process environment or the explicit `--env-file`, in addition to the existing exact
command confirmations. A local private key file must also be available before launch.
The preferred variable is
`LAMBDA_SSH_PRIVATE_KEY_PATH`; `LAMBDA_SSH_KEY` is accepted only as a compatibility
source when it names an existing local private key file directly or a simple filename
under `~/.ssh`, or when it contains OpenSSH public key material/comment that can be
matched to a local `~/.ssh/*.pub` file with a sibling private key. Inline private key
material and arbitrary relative paths are rejected.
A run may launch at most one instance, perform at most one bounded SSH
connectivity/authentication probe, and must terminate exactly the owned instance.

Before the SSH authentication probe, M055 now performs a bounded TCP readiness poll for
port 22 on the discovered host. If port 22 does not become reachable, M055 reports
`ssh_port_not_reachable` and skips the SSH process entirely. If port 22 becomes
reachable, M055 performs the single approved OpenSSH authentication probe and reports
any subsequent exit 255 as an SSH-layer failure rather than a provider metadata or
host-readiness failure.

M055 still forbids remote shell commands, command output collection, file transfer, port
forwarding, package installation, setup scripts, cloud-init, and training.
