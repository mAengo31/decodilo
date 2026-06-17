# Recovery Manifest Chain

Recovery manifests form a hash chain. Each new manifest may include the
previous manifest hash, and the latest manifest is also written to
`recovery_manifest.json` as the active pointer.

Chain validation checks:

- latest manifest discovery is deterministic
- the active pointer matches the newest intended manifest
- previous manifest hashes exist
- manifest hashes validate
- run id does not change inside the chain
- global version does not regress
- recovery does not silently fall back to an older checkpoint

For chunked checkpoint mode, the recovery manifest points to the primary
chunked checkpoint artifact. If that manifest or any required artifact hash
does not validate, recovery fails closed.

Useful command:

```bash
python -m decodilo.cli recovery validate-chain --workdir /tmp/decodilo-run
```

