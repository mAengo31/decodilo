# Lambda Python Runtime Command Policy

M064 prepares only a future M065 Python runtime version query.

The selected future command is exactly:

```bash
python3 --version
```

Forbidden:

- `python -c` or `python3 -c`
- module execution with `-m`
- script execution
- imports
- shell wrappers or command chaining
- `pip`, `conda`, `apt`, or package installation
- training, benchmarking, file transfer, and port forwarding

The policy is future-only. It does not authorize immediate launch, SSH, command
execution, package installation, or training.
