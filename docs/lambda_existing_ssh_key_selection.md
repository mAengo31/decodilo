# Lambda Existing SSH Key Selection

Strand-compatible launch payloads require an existing SSH key name in
`ssh_key_names`. M037R may select an existing key from read-only discovery or an
operator-selected existing key name, but it must not create, delete, or modify
SSH keys.

```bash
python -m decodilo.cli lambda strand ssh-key-selection \
  --discovery-report /tmp/decodilo-lambda-m037r-readonly-discovery.json \
  --out /tmp/decodilo-lambda-strand-ssh-key-selection.json
```

The selection artifact records a redacted/hash form for review and stores the
payload name only in local private artifacts. It must not store raw public key
material. If no existing key is discovered or selected, the lower-cost package
blocks before any future launch review.

M038 revalidates this artifact before producing lower-cost canonical readiness
and resource locks.

M039A execution uses the raw selected key name only inside request construction
for the Strand-compatible `ssh_key_names=[...]` payload. Public reports,
execution gates, command previews, and transport diagnostics must show only a
hash or redacted value. If the local private artifact does not contain the raw
existing key name, the lower-cost execution path halts before request
construction.
