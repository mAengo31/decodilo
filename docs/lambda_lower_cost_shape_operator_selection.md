# Lambda Lower-Cost Shape Operator Selection

M037 evaluates whether the lower-cost `gpu_1x_h100_pcie` lifecycle-smoke shape
should be selected for a future reauthorization package.

If support/operator evidence confirms the shape is supported for the target
account and region, the selection status is `select_lower_cost_shape`. If
support says it is unavailable, M037 blocks selection. If support evidence is
missing, M037 records `needs_operator_selection`.

Selecting a lower-cost shape does not change active launch artifacts. It only
requires future regeneration of M020, M028, M029, and downstream strategy
artifacts.
