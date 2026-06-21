# Lambda Endpoint Policy

The Lambda endpoint policy is fail-closed. It allows only explicit GET
endpoints for read-only discovery:

- instance types
- regions
- images
- SSH keys
- filesystems
- instances
- instance by ID
- quota
- usage estimate

All POST, PUT, PATCH, and DELETE requests are denied. Unknown GET endpoints are
also denied unless they are explicitly added to the allowlist. The policy cannot
be overridden by CLI config in M019.

M019A endpoint sets choose which allowlisted GET operations are attempted:
`minimal`, `standard`, or `extended`. They do not alter the denylist. Unknown
endpoints, all non-GET methods, and every launch/terminate/restart/create/delete
operation still fail closed before transport.
