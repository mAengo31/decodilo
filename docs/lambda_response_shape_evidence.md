# Lambda Response Shape Evidence

M036 response-shape evidence records what a successful launch and terminate
response should look like before any future launch attempt is considered.

Launch evidence must include either the exact field containing the instance ID
or an explicit explanation that the provider may return accepted/async success
without an instance ID. Terminate evidence must include terminal states and
read-only verification expectations.

Malformed, empty, or non-JSON responses remain future reconciliation cases. They
must not trigger automatic relaunch.
