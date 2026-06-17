# Price Tracker

Milestone 004 treats price data as provenance-bearing input, not hardcoded
truth. Tests still use local fixtures only; no network fetch is required.

## Price Snapshots

A `PriceSnapshot` is a versioned record of a pricing source:

- `snapshot_id`
- provider
- captured time
- source URL or file path
- source type
- source SHA-256
- parser version
- currency and tax flag
- normalized price records
- sample-data flag

Source types are:

- `fixture`
- `manual_html`
- `manual_json`
- `public_web`

Fixture snapshots must be marked `is_sample_data=true`.

## Price Records

Each snapshot record includes provider, product family, instance shape, GPU
type, GPU count, optional memory and region, per-GPU-hour price,
per-instance-hour price, currency, tax flag, source URL, captured time, and a
stable `record_id`.

Budget output includes both `snapshot_id` and `record_id` so later decisions can
be traced to exact data.

## Freshness

By default a snapshot older than 7 days is stale. Budget checks reject stale
snapshots unless `--allow-stale-prices` is passed explicitly. Unknown capture
timestamps are treated as unusable for guarded estimates.

## Sample Data

Sample fixture data is useful for tests and examples, but it is not planning
truth. Cloud-intended budget estimates reject sample snapshots unless
`--allow-sample-prices` is passed explicitly.

## Budget Manifests

`RunBudgetManifest` records the price snapshot, selected records, planned
instances and GPUs, planned hours, estimated GPU-hours, base cost, safety buffer,
credit projection, and override flags.

Local runs may include a manifest when pricing options are supplied. Future
cloud runs must require one before launch. No cloud launch exists in this
repository yet.

## Fail-Closed Behavior

The budget path fails closed when:

- no price matches
- multiple prices match and ambiguity is not explicitly allowed
- the snapshot is sample data and sample prices are not allowed
- the snapshot is stale and stale prices are not allowed
- the max run budget is exceeded
- safety-buffer-adjusted cost exceeds available credits

## Cloud Dry-Run Plans

Milestone 006 Lambda dry-run plans reuse price snapshots and budget manifests.
The plan records `price_snapshot_id`, `selected_price_record_id`, base cost,
safety-buffer-adjusted cost, projected remaining credits, and override flags.

The Lambda shape catalog contains no prices and is not live availability.
Planning prices must come from snapshots, and every generated cloud plan has
`launch_allowed=false`.
