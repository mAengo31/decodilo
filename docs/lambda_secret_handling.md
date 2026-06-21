# Lambda Secret Handling

Lambda API keys are billing credentials. M019 accepts a key from an explicit
local file:

```bash
--api-key-file /path/to/lambda_api_key.txt
```

M019C also supports an explicit project-local `.env` source when the operator
requests it:

```bash
--env-file .env --env-key LAMBDA_API_KEY
```

Decodilo does not accept `--api-key`, does not read OS environment variables,
does not auto-load `.env`, and does not serialize or print the key. The `.env`
parser only handles simple `KEY=VALUE` lines, strips surrounding quotes, rejects
missing/empty/multiline/oversized values, and reports only redacted metadata
such as `secret_source="env_file"`, `env_file_basename=".env"`,
`env_key="LAMBDA_API_KEY"`, `secret_loaded=true`, and `redacted=true`.

Secret files are rejected when missing, empty, oversized, multi-line, a
directory, or world-readable where portable permission checks can enforce that.
The explicit `.env` file must be untracked or ignored by git. If it is tracked
or not ignored, the loader emits a high-severity warning according to policy.

M019A public summaries also redact resource IDs according to the selected
redaction mode. Local private reports may keep instance IDs for ledger
reconciliation, but API keys, authorization headers, bearer tokens, key
material, and secret-like values must never appear in JSON reports or CLI
output.
