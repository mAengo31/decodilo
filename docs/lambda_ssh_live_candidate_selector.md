# Lambda SSH Live Candidate Selector

The M055D SSH live candidate selector chooses a future M056 candidate from an
already-captured read-only `/instance-types` discovery artifact. It does not call
Lambda itself.

Selection requires a live-advertised instance type, one existing SSH key
selection, quantity `1`, no filesystem, no setup or cloud-init, no training, a
Strand-compatible payload shape, and a buffered 30-minute estimate below `$50`.

Ranking prefers:

1. Live-available candidates.
2. Candidate/region pairs without a recent capacity rejection.
3. Lowest buffered 30-minute cost.
4. Single-GPU shapes.
5. Deterministic shape and region ordering.

For the current M055D discovery evidence, the expected candidate is
`gpu_1x_a10` in `us-east-1`, with price evidence sourced from read-only provider
instance-type metadata because the catalog snapshot does not include that shape.
