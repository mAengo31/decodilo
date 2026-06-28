# Lambda Linux/Python 3.10 Wheelhouse

M068W prepares a local dependency wheelhouse for future Lambda use. It targets
CPython 3.10 on manylinux x86_64 and does not call Lambda, SSH, upload files, or
install packages on Lambda.

The future Lambda run may only install from the uploaded local wheelhouse with
`--no-index` or equivalent local-only behavior.
