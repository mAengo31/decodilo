# M075R Runtime/Protocol Smoke Runbook Preview

M075R is a future supervised live Lambda milestone. It is not authorized by
this document alone.

Future M075R may run only after fresh read-only discovery, one-shot arming, and
operator confirmation. The planned remote command is the argv-token equivalent
of:

```bash
env PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src \
  python3 -m decodilo.cli dev runtime-smoke \
  --synthetic \
  --max-steps 1 \
  --out /tmp/decodilo-runtime-smoke.json
```

Future execution constraints:

- exactly one Lambda instance launch attempt
- exactly one sanitized source bundle upload
- exactly one sanitized dependency wheelhouse upload
- dependency installation only from the uploaded wheelhouse with no internet
- exactly one runtime/protocol smoke command
- stop at first failure
- bounded stdout/stderr capture with secret redaction
- no real training
- no data/model/package/code download
- no package installation from the internet
- no arbitrary shell, command chaining, redirects, pipes, or background process
- no port forwarding
- owned instance termination and read-only verification are required

The runbook preview remains non-executable with `launch_ready=false` and
`launch_allowed=false`.
