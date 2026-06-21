# Lambda Lower-Cost Shape Reauthorization

M036 reviews lower-cost catalog-backed Lambda shapes for lifecycle-only smoke
testing. It does not switch the active launch shape automatically.

The current lifecycle-smoke preference is to reauthorize a cheaper shape when
catalog evidence exists and support evidence does not contradict availability.
For the current catalog, `gpu_1x_h100_pcie` is lower cost than
`gpu_8x_h100_sxm`.

```bash
python -m decodilo.cli lambda lower-cost-shape review \
  --price-snapshot /tmp/decodilo-lambda-price-snapshot-real-catalog.json \
  --current-shape gpu_8x_h100_sxm \
  --out /tmp/decodilo-lambda-lower-cost-shape-review.json
```

Any shape change requires future M020/M028/M029 regeneration. M036 keeps
`launch_ready=false` and `launch_allowed=false`.

M037R narrows this into a Strand-compatible package for `gpu_1x_h100_pcie`.
That package also requires an existing SSH key selection, lower-cost price and
resource reconciliation, Strand compatibility evidence, and response-loss
controls. It can authorize only a future review, never immediate execution.
