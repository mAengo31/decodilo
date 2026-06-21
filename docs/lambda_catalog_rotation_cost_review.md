# Lambda Catalog Rotation Cost Review

M044 cost review validates the selected catalog-rotation candidate against the
non-sample Lambda price catalog.

It records:

- selected candidate, GPU type, and GPU count
- per-GPU and per-instance hourly pricing
- 30-minute estimated and buffered cost
- prior failed `gpu_1x_h100_pcie` buffered cost
- incremental cost versus the prior failed candidate
- warnings for catalog-only availability and larger-than-needed shape size

The review blocks sample pricing, missing candidate pricing, missing prior-shape
pricing, over-budget buffered estimates, and rotation artifacts that do not
select `gpu_8x_a100_80gb_sxm4`.
