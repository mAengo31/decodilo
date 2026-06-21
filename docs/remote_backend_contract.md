# Remote Backend Contract

The remote backend contract describes the future operations and capabilities
required for production artifact storage:

- artifact put/get/range/list/delete
- conditional manifest put
- atomic manifest commit
- artifact verification
- delete transactions
- lifecycle marks and listings
- health checks
- bandwidth and cost accounting

`DisabledRemoteArtifactBackend` advertises the contract surface but raises
`RemoteBackendDisabledError` for every operation. No real S3, GCS, Azure Blob,
Lambda storage, NFS, object-store SDK, credential flow, or network client exists
in this milestone.

Milestone 016 adds a provider-neutral conformance suite for this contract. The
disabled backend remains disabled and is not considered usable by conformance.
