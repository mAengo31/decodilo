# Lambda Mutation Safety Rehearsal

M021 rehearses mutation-shaped lifecycle logic without real mutation. Fake
launch and fake teardown commands are intentionally named and reported as fake,
use synthetic IDs, and operate only on local JSON state.

Safety boundaries:
- live read-only Lambda transport remains GET-only
- live read-only client mutation methods raise before transport
- fake lifecycle commands accept no API-key, env-file, live, or mutation flags
- no POST/PUT/PATCH/DELETE Lambda path is introduced
- `launch_ready=false` and `launch_allowed=false` remain enforced

This milestone validates control-plane journaling, idempotency, failure
injection, orphan detection, and teardown verification before a future milestone
can even design mutation-capable behavior.

M022 adds mutation-shaped fake endpoints, but they are deliberately local and
synthetic. They reject real Lambda URLs, reject API keys, and stay separate from
the live GET-only transport.

M023 adds a review-only real mutation boundary proposal. It can describe future
launch and terminate operation shapes as metadata, but it does not add a real
POST/PUT/PATCH/DELETE Lambda transport and cannot enable mutation or launch.

M024 adds a disabled real-mutation skeleton around that proposal. The skeleton
defines where future mutation transport, request building, idempotency, budget
locks, resource scope, and arming checks would connect, but every executable
path remains blocked. Mutation methods raise before request construction and
the skeleton audit proves no live mutation path exists.
