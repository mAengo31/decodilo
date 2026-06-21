# Remote Backend Credentials And Auth

Milestone 016 models future credential and authorization requirements without
accepting, reading, or printing secrets.

`SecretRef` is symbolic metadata only: name, provider, purpose, required flag,
rotation policy, and notes. Raw fields such as `secret_value`, `access_key`,
`secret_key`, `token`, `password`, and `private_key` are rejected.

Remote backend modules do not read cloud environment variables.

Auth scopes are least-privilege planning records for syncer manifest writes,
learner fragment writes, learner global-update reads, replay artifact reads, and
GC deletes.
