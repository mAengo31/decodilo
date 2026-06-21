# Lambda Capacity-Selected Launch Gate

The capacity-selected gate-check validates the future M046 review package. It
reports:

- selected candidate and source
- cost/risk review status
- operator approval status
- M046 authorization status
- response capture state
- effective launch timeout
- no automatic launch retry
- selected SSH key hash/redaction only

M046 also has an execution gate for the real command path. It validates:

- M046 authorization, cost/risk review, operator approval, and M045 report
- capacity-aware selector output, authorization, and gate-check
- selected candidate `gpu_8x_a100_80gb_sxm4`
- quantity `1`
- private raw SSH key name availability for request construction
- public SSH key hash/redaction for reports
- response capture, status-before-parse, timeout >= 30 seconds
- no automatic launch retry
- old M028/M029 fallback blocked
- M039 lower-cost fallback blocked

The gate is review-only. It does not launch, terminate, mutate Lambda
resources, or authorize immediate execution.
## M047 Region Evidence

Capacity-selected launch gates must treat the selected region as evidence-backed data.
For future lifecycle smoke launches, the region must be selected from the live regions
for the selected canonical shape id, using the live-region selection artifact instead of
manual artifact edits.
