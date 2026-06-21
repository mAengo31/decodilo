# Scaling Decision Report

`LearnerScalingDecisionReport` is the auditable output of the M014A learner-pod
planning layer.

It includes:

- scenario and calibration inputs
- objective
- all evaluated candidates
- recommended learner count, quorum, grace window, sync interval, and fragment count
- expected goodput and cost per useful token
- cost per sample-efficiency-adjusted token
- dominant bottleneck
- backend design targets
- sensitivity summary
- warnings and limitations
- `cloud_state.launch_ready=false`
- `cloud_state.launch_allowed=false`

Backend design targets include peak artifact read/write Gbps, artifact operations per
second, syncer merge Gbps, checkpoint growth, event-log growth, and replay snapshot
frequency. These targets inform a future remote artifact backend design, but they do
not validate a remote backend and do not permit cloud launch.

Milestone 015 uses these targets to generate `RemoteBackendRequirementSet`.
That requirement set bridges learner-pod planning and future remote artifact
backend design validation.
