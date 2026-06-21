# Lambda Fake Server

The Lambda fake server is an in-process facade over `FakeLambdaTransport`.
It intentionally does not open a network listener. If a host is provided, it
must be `127.0.0.1` or `localhost`; any public bind address is rejected.

The fake transport serves deterministic fixture data for regions, instance
types, images, SSH keys, filesystems, instances, quotas, and usage estimates.
It can simulate throttling, server errors, malformed responses, and logical
latency ticks without calling external services.

Mutating endpoints remain forbidden even when served by fake transport.
