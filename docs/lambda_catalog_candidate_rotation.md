# Lambda Catalog Candidate Rotation

Catalog candidate rotation ranks Lambda product-catalog shapes for future
lifecycle-smoke review after a selected shape repeatedly fails for capacity.

Inputs:

- non-sample Lambda price snapshot
- capacity history
- existing SSH key selection
- maximum budget

Default policy:

- exclude shapes with recent capacity errors
- require buffered 30-minute cost below budget
- require a Strand-compatible quantity-1 payload
- require an existing SSH key selection
- forbid setup scripts, cloud-init, user data, training, and filesystem
  creation

The ranked result is catalog evidence only. It is not live availability proof
and does not authorize launch.

An operator may later choose the selected catalog candidate for a future review,
but M043 keeps `launch_ready=false` and `launch_allowed=false`.

M044 records that later operator decision. Until M044 receives explicit accept,
wait, or manual-selection input, the selected catalog candidate remains
unauthorized.
