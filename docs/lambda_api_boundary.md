# Lambda API Boundary

Milestone 018 defines a Lambda Cloud API boundary without enabling Lambda Cloud.

The `decodilo.lambda_cloud` package contains typed fixture models, a disabled
client, a read-only client backed by local fixtures, a mutation guard, and
dry-run launch/teardown plans. It does not contain a real Lambda HTTP client,
does not read API keys, and does not launch, restart, terminate, create, or
delete any Lambda resource.

Allowed M018 surfaces:
- fixture parsing
- in-memory fake transport
- optional localhost-only fake server facade with no socket listener
- read-only discovery against fake data
- budget, ledger, launch-plan, teardown-plan, and preflight evidence models

Disallowed M018 surfaces:
- real Lambda API calls
- real Lambda credentials
- resource mutation
- public bind addresses
- launch or teardown execution

Future M019 read-only discovery must still pass through this boundary and must
not bypass the mutation guard or credential model.

## Milestone 019 Live Read-Only Mode

M019 permits a real Lambda API key only for `lambda live-discover` and only when
`--live-read-only` and `--api-key-file` are both provided. Read-only calls are
guarded before transport by the mutation guard and endpoint policy. Launch,
terminate, restart, create, delete, SSH, setup scripts, and training on Lambda
remain out of scope.
