# Lambda SSH Safe Client Command

M054A generates a non-executable OpenSSH preview for future connectivity checking.
The preview uses redacted key and host placeholders and includes safety options such as
`BatchMode=yes`, `RequestTTY=no`, `ClearAllForwardings=yes`, `ForwardAgent=no`,
`ForwardX11=no`, `PermitLocalCommand=no`, `ControlMaster=no`, and `SessionType=none`.

The preview includes no remote command argument and forbids `scp`, `sftp`, `rsync`,
local/remote/dynamic forwarding, agent forwarding, X11 forwarding, and TTY allocation.
Future M054B must still enforce a bounded local controller timeout.

M054A never executes the preview.
