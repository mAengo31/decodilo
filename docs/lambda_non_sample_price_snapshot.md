# Non-Sample Price Snapshot

First real launch planning cannot use packaged sample prices. A usable M029B price
snapshot must come from an explicit operator-provided catalog or manual JSON snapshot
with:

- `is_sample_data=false`
- `source_url`
- `source_sha256`
- `captured_at_utc`
- a matching instance price record

The snapshot remains planning evidence only. It does not prove live availability and
does not enable launch.
