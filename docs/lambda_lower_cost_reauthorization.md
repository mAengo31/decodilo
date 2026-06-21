# Lambda Lower-Cost Reauthorization

M037R reauthorizes only a future review path for the cheaper
`gpu_1x_h100_pcie` lifecycle-smoke shape. It does not authorize immediate
execution.

The package requires:

- Strand-compatible launch plan.
- Existing SSH key selection.
- Non-sample price reconciliation under the $50 budget.
- Read-only resource reconciliation with zero unmanaged billable resources.
- Strand compatibility evidence.
- Response-loss controls with timeout at least 30 seconds and no auto retry.

```bash
python -m decodilo.cli lambda lower-cost authorization-package \
  --launch-plan /tmp/decodilo-lambda-strand-lower-cost-plan.json \
  --ssh-key-selection /tmp/decodilo-lambda-strand-ssh-key-selection.json \
  --price-reconciliation /tmp/decodilo-lambda-lower-cost-price-reconciliation.json \
  --resource-reconciliation /tmp/decodilo-lambda-lower-cost-resource-reconciliation.json \
  --strand-compatibility /tmp/decodilo-lambda-strand-compatibility.json \
  --response-loss-controls /tmp/decodilo-lambda-strand-response-loss-controls.json \
  --out /tmp/decodilo-lambda-lower-cost-authorization-package.json
```

Any real launch remains a separate future milestone with fresh gates and
operator approval.

M038 builds the next authorization layer for future M039. The M039 record can
remain `not_authorized` if the operator approval artifact is only a template.
