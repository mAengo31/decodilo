# Lambda Mutation Feature Flags

M024 feature flags are intentionally one-way disabled.

Defaults:
- `real_mutation_feature_present=true`
- `real_mutation_transport_executable=false`
- `launch_execution_enabled=false`
- `termination_execution_enabled=false`
- `mutation_arming_allowed=false`

Environment variables, CLI flags, and config files cannot enable real mutation
execution. Attempts to construct enabled flag states fail validation.
