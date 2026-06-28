# Lambda GPU Visibility Success

M064 closes out the completed M063 GPU visibility query offline. It reads
persisted artifacts only and performs no Lambda call, SSH attempt, remote
command, file transfer, package installation, or training.

M063 is a full GPU visibility success only when the exact command succeeded and
the structured fields are preserved:

- GPU name
- `memory.total`
- driver version

If the command succeeded but only bounded redacted stdout hash evidence was
preserved, M064 records
`gpu_visibility_query_executed_output_hash_only`. That is closeout-successful
with a warning, not a reason to relaunch by itself.

M064 keeps `launch_ready=false`, `launch_allowed=false`, and
`billable_action_performed=false`.
