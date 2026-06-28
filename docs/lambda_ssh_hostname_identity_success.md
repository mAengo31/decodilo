# Lambda SSH Hostname Identity Success

M060 closes out the M059 hostname-only identity-command run using persisted
artifacts only. It does not call Lambda, open SSH, run commands, use
credentials, or spend money.

M060 classifies M059 as `ssh_hostname_identity_success` only when:

- the run ID is `lambda-m059-hostname-identity-command`
- launch and owned termination were both requested exactly once
- the launch response succeeded
- read-only verification saw the owned instance running
- host discovery found a provider metadata host
- TCP/22 became reachable
- SSH executed exactly `hostname`
- command exit status was `0`
- stdout was captured only as redacted/hash metadata
- raw stdout was not stored
- file transfer, port forwarding, package installation, and training were not
  attempted
- termination was verified
- final discovery has zero visible and zero unmanaged instances
- strict credential-pattern scanning passes

The closeout may record historical M059 billable activity, but M060 itself must
keep `launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false`.
