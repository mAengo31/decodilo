# Lambda SSH-Proven Candidate Policy

Future Decodilo remote vertical-slice attempts should prefer candidate and region pairs that have already proven SSH readiness.

A candidate/region pair is SSH-proven when prior evidence includes:
- launch request sent
- provider running verification
- host discovery
- TCP/22 readiness
- bounded SSH command success
- owned-instance termination verified

For the current history:
- preferred SSH-proven pair: `gpu_1x_a10` in `us-east-1`
- excluded by default: `gpu_1x_h100_sxm5` in `us-south-2`, because M067R found a host but TCP/22 did not become reachable

Fresh live availability alone is not enough to silently substitute an unproven candidate for a Decodilo source-bundle vertical slice.
