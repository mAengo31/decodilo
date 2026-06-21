# Lambda Launch Shape Strategy

The current planned shape is `gpu_8x_h100_sxm`. For lifecycle-only smoke testing,
M035 reviews lower-cost catalog shapes because no training, SSH, setup, or
cloud-init workload is planned.

A lower-cost shape may reduce spend exposure, but it is not selected
automatically. Any shape change requires regenerated price/resource evidence and
future M020/M028/M029 authorization artifacts.

Public catalog price evidence is not live availability evidence.

M036 turns the M035 lower-cost recommendation into a reauthorization review. For
the current catalog-backed prices, `gpu_1x_h100_pcie` is the lower-cost
lifecycle smoke candidate, but using it still requires future regeneration of
the launch authorization artifacts.
