# Lambda Real Mutation Absence Audit

The real mutation absence audit scans Lambda and cloud code for accidental real
mutation paths.

It checks for:
- live HTTP `POST`, `PUT`, `PATCH`, or `DELETE` support in the live transport
- live launch/terminate CLI commands
- mutation enable flags
- hardcoded `launch_allowed=true` patterns in Lambda live code

The audit deliberately ignores fake mutation modules because those are local
rehearsal code. A passing audit means no real Lambda mutation implementation was
found; it does not approve future launch.
