# Lambda Remote Command Allowlist

M050 command allowlists are future-only and non-executable. The default
metadata-only profile has an empty command list.

M057 proved only the no-op command `true`. M058 does not expand the general
allowlist for immediate use; it authorizes only a future M059 identity-command
review. The current selected future command is `hostname`.

M061 later proved `whoami`. M062 closes that run offline and defines only a
future M063 GPU visibility review.

Potential future commands are exact-match allowlist entries such as:

- `hostname`
- `whoami`
- `nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader`
- `python --version`

Only the exact `nvidia-smi --query-gpu=... --format=csv,noheader` command is in
scope for the future M063 review. Python remains a later-stage example, not an
approved command.

Commands with shell chaining, pipes, redirects, `curl`, `wget`, `apt`, `pip`,
`conda`, `git`, `docker`, `nohup`, background execution, or training terms are
rejected.
