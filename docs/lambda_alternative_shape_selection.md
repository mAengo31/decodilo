# Lambda Alternative Shape Selection

After repeated capacity rejection, an operator-facing selection record can choose
one future-review path:

- wait for live availability evidence
- use the ranked catalog candidate
- manually select a catalog-backed shape
- pause launch attempts

Only one choice may be present.

Manual shape selection requires a non-sample catalog price. Catalog candidate
selection still requires operator risk acceptance in a later launch milestone
because catalog evidence is not live availability proof.

The selection record never authorizes immediate execution and must keep
`launch_ready=false` and `launch_allowed=false`.

M044 turns the M043 catalog-candidate selection into an explicit operator
decision. Acceptance can authorize only a future M045 review; decline creates a
wait or manual-selection path.
