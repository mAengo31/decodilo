# Lambda No-Training Policy

M050 and the default future M051 bootstrap review do not approve training.

Forbidden work includes:

- trainer execution
- model training
- dataset download
- model download
- token processing benchmark
- GPU benchmark beyond a bounded visibility query
- long-running process

The lifecycle smoke proved launch and owned termination. Runtime bootstrap must
preserve that safety boundary before any broader remote workload is considered.
