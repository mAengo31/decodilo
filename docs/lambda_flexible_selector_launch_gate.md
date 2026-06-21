# Lambda Flexible Selector Launch Gate

The flexible selector gate check verifies the future-review package only. It
does not launch or authorize immediate execution.

The gate reports:

- selected candidate
- selected candidate source
- selected candidate reason
- estimated and buffered 30-minute costs
- SSH key availability by hash/redaction only
- response capture status
- no automatic launch retry
- Strand payload compatibility
- `fixed_shape_path_used=false`

If no live-available candidate exists, catalog-only output can pass the gate
only when the selector output records explicit catalog-only risk acceptance.

For M044H and later, the gate also reports recent capacity-failure exclusions.
A selected candidate with recent capacity failure cannot pass through the
generic catalog-only path. It needs fresh live availability evidence or a
separate same-shape capacity retry acceptance artifact for future review.
