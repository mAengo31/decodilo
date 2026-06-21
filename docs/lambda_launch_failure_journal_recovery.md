# Lambda Launch Failure Journal Recovery

If `report.json` is missing after a launch attempt, M034D can recover incident
state from the append-only launch journal.

Recovery detects:

- whether `m029_launch_request_sent` occurred;
- whether a response or timeout event was journaled;
- whether an owned instance ID was recorded;
- whether termination was requested or verified.

Recovered state blocks future launch until incident closeout and crash-safe
diagnostics hardening pass.
