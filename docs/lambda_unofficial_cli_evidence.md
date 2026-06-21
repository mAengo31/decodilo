# Lambda Unofficial CLI Evidence

The Strand-AI `lambda-cli` is explicitly unofficial. It must not be represented
as Lambda support confirmation, product documentation, or provider endorsement.

Allowed use:

- Compare local request and response shapes to a known-working operator-tested
  implementation.
- Record behavioral evidence for future review.
- Improve fake fixtures and parsers.

Forbidden use:

- Treating the CLI as authority to launch immediately.
- Weakening endpoint policy or mutation guard.
- Sending live POST/PUT/PATCH/DELETE requests during evidence review.
- Replacing required operator approval for future launch attempts.

M036R remains review-only. Future launch milestones still need fresh gates,
operator confirmation, one-instance scope, termination verification, and no
automatic retry on ambiguous launch responses.
