# Lambda GPU Visibility Output Policy

M063 GPU visibility output is limited to bounded stdout/stderr from the exact
future query.

Allowed fields:

- GPU name
- total GPU memory
- driver version

Output format must be `csv,noheader`. Stdout and stderr are capped at 4096 bytes
each. Secret redaction remains mandatory, and private key material must never be
serialized.

M062 does not authorize immediate command execution or output collection.
