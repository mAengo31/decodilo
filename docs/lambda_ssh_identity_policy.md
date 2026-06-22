# Lambda SSH Identity Policy

Future SSH-connectivity probes must use a single explicit identity reference:

- `IdentitiesOnly=yes` is required
- exactly one identity file/reference is allowed
- SSH agent identities are not allowed
- `ForwardAgent=no` is required
- identity paths are redacted in public artifacts
- raw SSH key names and private key paths must not be public

This policy is offline-only in M055B.
