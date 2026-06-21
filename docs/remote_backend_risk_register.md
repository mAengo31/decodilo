# Remote Backend Risk Register

The risk register records required risks for future remote backend work:

- credential leakage
- overbroad credentials
- stale manifest reads
- corrupted artifact reads
- unauthorized artifact deletes
- partial write visibility
- GC deleting live artifacts
- runaway storage cost
- bandwidth saturation
- backend throttling
- replay using the wrong artifact version
- data exfiltration
- missing audit logs
- orphaned cloud resources if future launcher work is coupled incorrectly

Critical open risks block SDK review. Mitigated risks require evidence
references.
