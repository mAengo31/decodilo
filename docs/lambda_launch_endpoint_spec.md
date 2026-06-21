# Lambda Launch Endpoint Spec

M032 records launch and termination endpoint specs from docs or operator
evidence without calling mutation endpoints.

Endpoint specs include operation, method, path template, source, source URL,
schema summaries, confidence, and notes. Low or unknown confidence blocks
response-loss hold release.

The endpoint verification command is offline and cannot authorize launch.
`launch_ready=false` and `launch_allowed=false` remain enforced.

M036R adds `unofficial_cli_behavior` as an endpoint-spec source for the
operator-tested Strand-AI `lambda-cli`. That source can support compatibility
review, but it remains unofficial and should be reported separately from Lambda
support confirmation or official documentation.
