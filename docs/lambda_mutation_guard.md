# Lambda Mutation Guard

`LambdaMutationGuard` is fail-closed.

Read-only allowlist:
- `list_instance_types`
- `list_regions`
- `list_images`
- `list_ssh_keys`
- `list_filesystems`
- `list_instances`
- `get_instance`
- `get_quota`
- `get_usage_estimate`

Mutation denylist:
- `launch_instance`
- `terminate_instance`
- `restart_instance`
- `create_ssh_key`
- `delete_ssh_key`
- `create_filesystem`
- `delete_filesystem`

Unknown operations are denied by default. The guard has no configuration switch
that enables mutation in M018.

In M019 the same guard is enforced before the live HTTP transport constructs a
request. Endpoint policy then independently denies non-GET and unknown
endpoints.
