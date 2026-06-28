# Lambda Remote Command Stage Policy

Remote command capability is staged. M058 accepts only the completed no-op
stage:

```text
current_accepted_stage = noop_command_only
```

The only future review stage opened by M058 is an identity-command review. The
default selected future command set is:

```text
hostname
```

M058 does not authorize immediate execution. The following remain denied:

- arbitrary shell
- command chaining, pipes, and redirects
- `nvidia-smi`
- remote `python`
- package installation
- file transfer
- port forwarding
- training

Future milestones must continue to use explicit operator approval, one-shot
arming, owned-instance termination, and read-only termination verification.

