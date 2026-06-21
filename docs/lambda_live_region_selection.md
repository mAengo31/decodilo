# Lambda Live Region Selection

M047 makes live-region selection auditable.

For a selected Lambda shape, the launch region must be one of the regions returned by
fresh read-only `/instance-types` evidence. Selection preference is:

1. explicit operator-approved region if it is live,
2. prior successful region if it is still live,
3. deterministic sorted live region fallback.

For the M046C success record, `gpu_8x_a100_80gb_sxm4` resolves to `us-midwest-1`
because that region was both live and successful. Stale regions, such as `us-west-1`
for this shape, must block.
