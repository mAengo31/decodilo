# Lambda Shape And Price Evidence

M029B separates Lambda launch evidence into distinct classes:

- live API discovery: read-only account and resource state.
- live availability evidence: only valid when endpoint semantics are known.
- public product catalog evidence: product and advertised price evidence.
- non-sample price snapshot: operator-provided planning price evidence.
- planned launch shape: the operator-selected first-launch shape.

An empty live `instance_types` response is not treated as proof that a shape does not
exist unless the endpoint semantics are known. It is classified as inconclusive and
must be paired with catalog, price, and operator-selected shape evidence before a
future launch gate can proceed.

M029B does not launch, terminate, mutate, or spend.
