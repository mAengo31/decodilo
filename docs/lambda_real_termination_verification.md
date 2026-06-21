# Lambda Real Termination Verification

M029 termination is owned-resource only. The owned instance ID must come from
the launch response or read-only reconciliation after a lost response.

Verification uses Lambda read-only get/list evidence. OS shutdown is
insufficient and is never considered termination.

If termination cannot be verified before timeout, the report must set
`manual_review_required=true`. The run journal and ledger are the recovery
artifacts for manual review.

If no owned instance ID is recorded after a lost launch response, automation must
not terminate anything. M029D requires manual console confirmation and discovery
diff evidence before the incident can close.
