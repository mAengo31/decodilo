# Lambda M051 Execution Reviewer Bridge

The M051 reviewer bridge is the only artifact allowed to expose:

```json
{
  "one_shot_request_send_permitted": true
}
```

The bridge can become ready only when the one-shot arming artifact is armed and
unexpired, command binding passes, artifact binding passes, and the standing
artifacts still keep launch disabled. It does not set `launch_ready` or
`launch_allowed`.

Future M051B execution must pass the bridge, artifact binding, and arming gate
flags to `lambda m029 run`. Missing or expired bridge evidence halts before
request construction.
