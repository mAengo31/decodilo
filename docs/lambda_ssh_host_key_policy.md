# Lambda SSH Host-Key Policy

Future SSH-connectivity probes must use a run-scoped isolated `known_hosts` file.
They must not modify global `~/.ssh/known_hosts`.

For ephemeral lifecycle probes, `StrictHostKeyChecking=accept-new` may be used only
when recorded by policy. `StrictHostKeyChecking=no` is forbidden. Host-key material
must not be serialized in public artifacts; fingerprints or hashes may be recorded
when needed.
