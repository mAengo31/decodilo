# Lambda Support Response Ingestion

M037 ingests a real support/operator response only when one is present, usually
at `/tmp/operator-support-response.json`.

The response may come from a Lambda support ticket, an operator-confirmed
official docs excerpt, or an operator manual confirmation based on official
docs. It must not contain API keys, Authorization headers, bearer tokens,
passwords, private keys, or other secret-like values.

If the response file is absent, M037 must not fabricate answers. The decision
remains `require_more_support_evidence` and endpoint confidence cannot upgrade.

All M037 ingestion and validation commands are offline and review-only.
