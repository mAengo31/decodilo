# Lambda SSH Provider Key Attachment Diagnostic

M055B reviews provider key evidence offline. The M055 diagnostic found:

- the selected key hash was `sha256:e8bd9b2e6fc17b09`
- the local private key matched the `.env` public key identity
- the provider key record was found by hash/redacted matching
- Lambda read-only SSH key records did not expose a `user_id` field

Missing provider `user_id` is not itself a blocker. A mismatch between selected
launch key evidence and local private-key identity blocks future SSH review.
