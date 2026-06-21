# Lambda Endpoint-Spec Operator Confirmation

M033 requires an operator to confirm the launch and terminate endpoint specs
before any future M034 review can proceed.

If the endpoint spec confidence is `medium`, the operator must explicitly accept
that confidence. Without that acceptance, the third-attempt authorization blocks.

The confirmation records launch and terminate operation names, methods, path
templates, source URL, and notes. It does not call Lambda mutation endpoints and
cannot enable launch.
