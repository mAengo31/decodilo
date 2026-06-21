# Lambda Metadata Bootstrap Arming Policy

Metadata-only bootstrap remains a supervised lifecycle operation:

- launch at most one instance
- collect provider/API-visible metadata only
- do not SSH
- do not run remote commands
- do not install packages
- do not train
- do not retry after response loss, malformed response, capacity rejection, or
  any 4xx/5xx response
- terminate exactly the owned instance if one is created
- verify termination through read-only Lambda discovery/list/get

M051A performs no launch, termination, live read-only API call, credential use,
SSH, remote command, package install, training, or billable action. It only
creates a reviewer-compatible one-shot bridge for a future supervised M051B
attempt.
