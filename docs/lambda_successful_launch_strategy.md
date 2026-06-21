# Lambda Successful Launch Strategy

After M046C, future lifecycle-smoke strategy should use:

- live `/instance-types` parsing,
- live region selection,
- canonical live Lambda shape ids,
- flexible availability-first selection,
- no hardcoded stale shape names.

The current successful shape/region pair is `gpu_8x_a100_80gb_sxm4` in `us-midwest-1`.
That result is evidence for future planning, not standing authorization for another
billable launch. Any future real launch still needs fresh read-only discovery, explicit
operator approval, response-loss controls, no automatic retry, and same-run owned
termination verification.

The next strategy stage is remote runtime bootstrap planning. The default bootstrap path
is metadata-only: no SSH, no remote command execution, no package installation, and no
training unless later milestones add explicit approvals while preserving same-run owned
termination verification.
