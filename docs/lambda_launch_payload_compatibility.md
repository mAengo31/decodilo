# Lambda Launch Payload Compatibility

M036R aligns the launch and terminate payloads with the Strand-AI CLI behavior.

Launch payload:

```json
{
  "region_name": "us-west-1",
  "instance_type_name": "gpu_1x_h100_pcie",
  "ssh_key_names": ["existing-key-name"],
  "quantity": 1
}
```

Optional launch fields:

- `name`
- `file_system_names`

The lifecycle smoke policy still forbids setup scripts, cloud-init/user data,
training workloads, multi-node launches, restart, and create/delete resource
operations.

Terminate payload:

```json
{
  "instance_ids": ["owned-instance-id"]
}
```

Terminate compatibility accepts a successful 2xx status with an empty response
body. Termination is still not considered complete until read-only verification
shows terminal or absent state for the owned instance.

For M037R, the lower-cost lifecycle-smoke plan uses the same payload shape with
`instance_type_name=gpu_1x_h100_pcie`. Missing existing SSH key names block the
package before any future launch review.
