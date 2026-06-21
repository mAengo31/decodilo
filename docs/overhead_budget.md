# Overhead Budget

Overhead budgets compare a performance characterization report against explicit
operator-provided thresholds. There are no hidden production thresholds.

```bash
python -m decodilo.cli perf check-budget \
  --report /tmp/decodilo-m014-perf/perf_characterization.json \
  --budget-json /tmp/decodilo-m014-perf/overhead_budget.json
```

Example budget:

```json
{
  "max_artifact_io_time_fraction": 0.5,
  "max_merge_time_fraction": 0.5,
  "max_checkpoint_time_fraction": 0.25,
  "max_artifact_bytes_per_useful_token": 1000000,
  "fail_on_budget_exceeded": true
}
```

If `fail_on_budget_exceeded` is true, exceeded or missing required metrics
produce errors. If false, they produce warnings.

