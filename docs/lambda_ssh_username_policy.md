# Lambda SSH Username Policy

M055B makes the future SSH username explicit. The default selected username is
`ubuntu`, sourced from the Lambda SSH-connectivity planning default.

Rules:

- the username must be explicit in future command previews
- implicit local usernames are forbidden
- `root` is blocked unless future operator override evidence exists
- empty usernames block

The username is not treated as a secret, but it is reported deliberately.
