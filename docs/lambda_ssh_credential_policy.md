# Lambda SSH Credential Policy

M053 may reference an existing SSH key selection by hash or redaction only. It
must not create or delete SSH keys, serialize private key material, serialize raw
public key material, or approve private key access.

An SSH key attached to a provider launch payload is not SSH usage. Future M054
must explicitly specify key source handling without embedding secret material.

## M054A private-key reference boundary

M054A may prepare a future private-key reference policy for M054B, but it must
not read, validate, serialize, or print private key material. Public key material
is also forbidden in public artifacts.

Allowed M054A evidence is limited to:

- existing SSH key selection by hash/redaction
- a redacted symbolic private-key reference placeholder
- a statement that future M054B must supply an operator-approved key source
  without embedding secret material

The actual safe SSH command preview must contain only redacted placeholders for
the private key reference and host. It must not contain raw key names, private
key material, public key material, credentials, or connection targets.
