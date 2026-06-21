# Lambda Package Install Policy

Package installation is denied by default for remote bootstrap planning.

Blocked examples include:

- `pip install`
- `python -m pip install`
- `apt install`
- `apt-get install`
- `conda install`
- `git clone`
- `docker pull`
- `curl` or `wget` download paths

Future bootstrap work should first use the image state already present on the
instance or metadata-only checks. Any package installation would require a later
explicit approval milestone.
