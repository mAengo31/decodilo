# Lambda M029 Emergency Stop

M029 emergency stop is scoped to the owned instance ID recorded in the journal
or ledger. It may not terminate any unowned discovered instance.

The command requires an explicit terminate-owned confirmation and must perform
read-only termination verification afterward. If the owned instance ID is
missing or the ledger does not authorize it, emergency stop blocks and requires
manual review.
