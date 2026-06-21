# Product Catalog Vs Availability

The Lambda public instances catalog can prove that a product and advertised price
were published at a captured source URL. It cannot prove that the account can launch
that product in a region at a future moment.

M029B records this distinction explicitly:

- `public_product_catalog` is product evidence.
- `price_snapshot` is price evidence.
- `live_api_discovery` is account/resource state evidence.
- `availability_evidence.endpoint_inconclusive` means live availability is unknown.

Future first-launch review may proceed with unknown live availability only when the
operator accepts that availability is discovered by the launch attempt itself and all
other gates pass.
