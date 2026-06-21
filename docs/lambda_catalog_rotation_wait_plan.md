# Lambda Catalog Rotation Wait Plan

If the operator declines the selected catalog-rotation candidate, M044 can
produce a wait-for-live-availability plan.

The wait plan:

- does not launch
- does not mutate Lambda resources
- permits read-only discovery only when the operator requests it
- treats product catalog entries as catalog evidence, not live availability
- keeps `launch_ready=false` and `launch_allowed=false`

The wait path is a valid M044 outcome and does not create an M045 authorization.
