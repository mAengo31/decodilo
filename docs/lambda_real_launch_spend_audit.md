# Lambda Real Launch Spend Audit

M029 spend audit estimates spend from the selected hourly price and elapsed
runtime. It does not require a live billing API.

Hard limits remain:
- max budget: `$50`.
- max runtime: `30` minutes.
- max instances: `1`.

If elapsed runtime exceeds the limit, or termination is not verified after a
sent launch request, the audit records warnings and manual review evidence.
