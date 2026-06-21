# Lambda Catalog Availability Launch Gate

The M041 catalog availability gate checks that the future M042 package is
internally consistent:

- M042 authorization is future-authorized
- availability plan still selects `gpu_1x_h100_pcie`
- catalog-only risk acceptance is complete
- response capture and no-retry controls remain active
- existing SSH key selection is present
- launch flags remain false

The command preview generated from this gate is non-executable. M042 must still
rerun fresh gates and collect immediate operator confirmation before any
billable request is considered.
