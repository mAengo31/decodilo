# Lambda M028 Decision Record

The M028 decision record may emit only:
- `blocked`
- `needs_more_evidence`
- `authorized_for_m029_one_instance_launch_attempt`

The positive status is authorization for the next milestone only. It is not
launch approval and cannot enable real mutation in the M028 build.

Forbidden outcomes such as launch-now approval, enabled mutation, or executable
launch remain invalid.

