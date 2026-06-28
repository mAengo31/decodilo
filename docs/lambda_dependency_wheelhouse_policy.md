# Lambda Dependency Wheelhouse Policy

Wheelhouse preparation rejects source distributions, local site-packages copies
with incompatible platform artifacts, macOS wheels, and Python 3.13 ABI wheels.

Controlled local wheel download is allowed only with explicit operator approval.
It downloads binary wheels on the development machine and never authorizes
Lambda-side internet access.
