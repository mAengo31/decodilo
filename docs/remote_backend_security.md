# Remote Backend Security

Milestone 015 adds a threat model and security checklist for a future remote
artifact backend.

Threats include artifact corruption, stale manifest reads, malicious artifact
refs, URI injection, credential leakage, unauthorized reads/deletes, replay with
wrong artifact versions, partial writes, rollback attacks, poisoned global
updates, data exfiltration, and deletion of live artifacts.

The checklist requires authentication, scoped credentials, no credentials in
logs, encryption in transit and at rest, client-side hash validation,
conditional manifest put, object versioning, delete transaction logs, lifecycle
policy, audit logs, and separate worker/syncer artifact scopes.

No real signing or encryption implementation is introduced here. Secret values
must not be supplied to the model; only redacted credential names are allowed.

Milestone 016 adds symbolic `SecretRef`, scoped auth, encryption, and integrity
policy models. Raw secret fields are rejected, and generated reports must not
print secret values.
