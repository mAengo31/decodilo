# Lambda GPU Visibility Parsed Output Audit

The parsed output audit determines whether M063 retained field-level GPU
visibility evidence or only a redacted stdout hash.

Statuses:

- `parsed_fields_present`: GPU name, memory total, and driver version are present.
- `output_hash_only`: the query succeeded, but only a hash/redacted output marker
  is available.
- `missing_output`: neither parsed fields nor output hash evidence is available.

`output_hash_only` is acceptable for M064 closeout with a warning because the run
still proved command execution, SSH connectivity, and clean teardown. A future
milestone can choose to rerun with parsed field capture if field values are
needed.
