# Chunked Storage

Milestone 008 adds `src/decodilo/storage`, a local filesystem package for
binary-safe, content-addressed artifacts.

## Content-Addressed Chunks

Chunks are stored by SHA-256:

```text
<store>/chunks/<first-two-hex>/<sha256>
```

Writing the same bytes returns the same hash. Reading a chunk recomputes the
hash and rejects corrupted bytes.

## Artifact Manifests

`StorageArtifactManifest` records:

- artifact id and type
- schema and codec version
- run id
- total bytes
- chunk size
- chunk hashes
- root hash
- manifest hash
- compression mode, currently `none`
- metadata

Manifest JSON is deterministic with sorted keys. Changing metadata or chunk
hashes changes the manifest hash.

## Inspect And Verify

```bash
python -m decodilo.cli storage inspect-artifact path/to/manifest.json
```

`inspect-artifact` prints at least:

- `artifact_id`
- `total_bytes`
- `chunk_count`
- `root_hash`
- `manifest_hash`
- `storage_root`

```bash
python -m decodilo.cli storage verify-artifact path/to/manifest.json
```

If the manifest has been copied away from its chunks, pass an explicit chunk
store root:

```bash
python -m decodilo.cli storage verify-artifact \
  /tmp/copied/manifest.json \
  --chunk-root /tmp/original/store
```

Moving a manifest and its `chunks/` directory together preserves verification.
Moving the manifest without chunks fails clearly with a missing chunk error.

## Atomic Writes

Chunks and manifests are written through temp files and then renamed into place.
If manifest commit fails, no valid committed manifest is produced.

## Backend Boundary

Only the local filesystem backend exists in this milestone. The package names
and manifest structure leave room for future remote storage, but no S3, GCS, or
cloud storage client is implemented.

Milestone 009 uses these local manifests as live learner-fragment and
global-update payload references. The runtime still passes only local
filesystem `ArtifactRef` metadata over JSONL transport; it does not fetch remote
objects or call cloud APIs.

Milestone 010 adds `tensor_binary_v1` artifacts on top of the same local chunk
store. Tensor artifacts store raw contiguous tensor bytes and deterministic JSON
metadata for dtype, shape, byte order, byte ranges, and checksums. This remains
local filesystem storage; remote artifact backends are represented only by a
disabled stub.

## Retention And GC

Milestone 012 adds artifact indexing, reachability analysis, and dry-run-first
garbage collection. The reachability graph protects run specs, final reports,
artifact manifests, recovery manifests, latest checkpoints, latest global
states, replay snapshots, and event segments required by recovery.

Use:

```bash
python -m decodilo.cli artifacts index --workdir /tmp/decodilo-run --out /tmp/decodilo-run/artifact_index.json
python -m decodilo.cli artifacts gc-plan --workdir /tmp/decodilo-run --out /tmp/decodilo-run/gc_plan.json
```

Deletion requires `artifacts gc --apply` and still refuses to delete protected
artifacts.

Milestone 013 adds artifact reference audit and transaction-safe GC apply.
Audits compare normalized paths, verify hashes, and fail when event logs or
recovery manifests reference artifacts missing from `artifacts.json`. GC apply
records a transaction and stages deletes under `.decodilo_trash/` so partial
failures are visible and retained artifacts remain verifiable.
