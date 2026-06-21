# Lambda Catalog Rotation Shape Authorization

The M045 catalog-rotation authorization package can only authorize a future
review. It requires:

- repeated capacity history for the prior failed shape
- same-shape retry blocked by capacity-aware retry policy
- rotation rank selecting `gpu_8x_a100_80gb_sxm4`
- cost review passed below the $50 budget
- complete risk acceptance
- operator decision accepting the selected candidate
- existing SSH key selection
- response-loss controls with no automatic launch retry

The only successful status is
`authorized_for_future_m045_catalog_rotation_launch_review`. Immediate execution
remains disabled.
