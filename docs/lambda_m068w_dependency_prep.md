# M068W Dependency Prep

M068W exists because M067R3 reached Decodilo source import but failed CLI startup
on missing `pydantic`. M068W creates a hash-locked, secret-scanned, compatibility
audited wheelhouse bundle for a future M068R retry.

Standing launch flags remain `launch_ready=false` and `launch_allowed=false`.
