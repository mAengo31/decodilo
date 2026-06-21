# Lambda Remote Command Allowlist

M050 command allowlists are future-only and non-executable. The default
metadata-only profile has an empty command list.

Potential future commands are exact-match allowlist entries such as:

- `hostname`
- `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader`
- `python --version`

Commands with shell chaining, pipes, redirects, `curl`, `wget`, `apt`, `pip`,
`conda`, `git`, `docker`, `nohup`, background execution, or training terms are
rejected.
