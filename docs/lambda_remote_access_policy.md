# Lambda Remote Access Policy

The default remote access mode is provider metadata only. Attaching an existing
SSH key to a Lambda launch payload does not approve SSH use.

Policy invariants:

- no SSH without explicit operator approval
- no interactive shell
- no arbitrary shell command
- no file transfer unless a later approval explicitly adds it
- no package installation
- no training
- no background command

M050 only writes policy artifacts for future review. It does not connect to any
remote instance.

M053 narrows the next review step to SSH connectivity only. That planning layer
still forbids interactive shells, remote command execution, file transfer, port
forwarding, package installation, and training. It does not approve SSH now.
