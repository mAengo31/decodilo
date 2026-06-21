# Lambda M034 Authorization Record

The M034 authorization record can only authorize a future review:
`authorized_for_future_m034_third_launch_attempt`.

It cannot authorize:

- launch now;
- termination now;
- restart;
- SSH;
- setup scripts;
- cloud-init;
- training;
- create/delete SSH keys or filesystems;
- automatic relaunch after response loss;
- termination of medium, low, or no-confidence candidates.

Even when authorized for future M034 review, `launch_ready=false`,
`launch_allowed=false`, and `real_mutation_enabled=false` remain enforced.
