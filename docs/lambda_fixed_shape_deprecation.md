# Lambda Fixed Shape Deprecation

Fixed-shape launch-review artifacts are deprecated for flexible availability
selection. Future flexible-selector reviews must not derive selected shape from
hardcoded `gpu_1x_h100_pcie` or `gpu_8x_a100_80gb_sxm4` paths.

The selected shape source must be the selector output. Command previews must
reference flexible selector authorization and selector output, not old M039 or
M045 fixed-shape authorization artifacts.

Capacity history is part of the selector source of truth. A hardcoded fallback
to `gpu_1x_h100_pcie` is forbidden after capacity history marks that shape as
recently capacity-failed unless the future review uses fresh live availability
evidence or the explicit same-shape retry acceptance path.

This deprecation does not remove historical artifacts. It prevents those
artifacts from being used as the source of a future flexible-selector launch
target.
