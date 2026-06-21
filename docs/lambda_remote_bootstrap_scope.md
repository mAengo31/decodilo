# Lambda Remote Bootstrap Scope

M050 defines the first safe post-lifecycle Lambda runtime bootstrap review. It is
planning-only: no Lambda API call, SSH session, remote command, package install,
or training is performed.

Default M051 scope is `lifecycle_plus_metadata_only`:

- launch exactly one approved instance in a future supervised milestone only
- verify owned instance through Lambda read-only get/list
- collect provider/local metadata only
- terminate exactly the owned instance in the same supervised run
- verify terminal or absent state through Lambda read-only discovery/list/get

SSH connectivity and single-command modes require separate future approval
artifacts. Training, package installation, setup scripts, cloud-init, downloads,
background processes, and unattended execution remain forbidden.

## M052 Closeout

M052 closes out the successful M051B metadata-only bootstrap from persisted local
artifacts only. It does not call live Lambda APIs, use credentials, SSH, run
remote commands, install packages, train, or authorize immediate launch.

The M052 strategy update may recommend future SSH-connectivity planning, but SSH
and remote command execution remain unapproved until a separate supervised
milestone explicitly authorizes them.
