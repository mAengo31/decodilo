# Lambda M034 Future Launch Hold

The M034 future launch hold blocks any later launch review while either:

- the M034C incident is open or unresolved; or
- crash-safe diagnostics hardening has not been accepted.

When both are resolved, the hold can clear only for a future review. It never
sets `launch_ready=true` or `launch_allowed=true`, and it never authorizes a
launch by itself.
