# Lambda Catalog Availability M042 Authorization

M041 can create a future-only M042 authorization if the operator accepts the
catalog-only availability risk.

Required evidence:

- capacity-error closeout succeeded
- availability-first authorization exists
- availability-first go/no-go passed
- catalog availability risk acceptance is complete
- operator decision accepts catalog-only availability risk
- selected candidate is `gpu_1x_h100_pcie`
- buffered 30-minute estimate is below $50
- existing SSH key selection is present
- response-loss controls pass
- automatic launch retry is disabled

The only passing status is
`authorized_for_future_m042_catalog_availability_launch_review`. It authorizes a
future review milestone only. It does not authorize launch now.
