# Lambda SSH Redacted Stderr Capture

Future SSH-connectivity probes should persist bounded redacted stderr for failed
OpenSSH invocations:

- maximum stderr bytes: 8192
- maximum lines: 80
- stdout remains empty for connectivity-only probes
- private key paths, raw SSH key names, host/IP values, API keys, bearer tokens,
  Authorization headers, private key material, public key material, and sensitive
  known-hosts paths are redacted

M055B defines this policy offline only. It does not execute SSH or read private keys.
