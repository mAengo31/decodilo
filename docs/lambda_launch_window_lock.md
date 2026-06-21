# Lambda Launch Window Lock

The M028 launch-window lock records the operator and timing constraints a future
M029 launch attempt must obey.

Defaults:
- operator present
- background execution forbidden
- automatic launch retry forbidden
- maximum launch attempts: 1
- maximum runtime: 30 minutes

Expired windows and background execution are invalid. The lock is review-only
and cannot enable launch.

