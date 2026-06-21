from decodilo.storage.remote_backend_auth_model import (
    AuthScopePolicy,
    default_auth_scope_policy,
    evaluate_auth_scope_policy,
)


def test_default_auth_scope_policy_passes() -> None:
    report = evaluate_auth_scope_policy(default_auth_scope_policy())

    assert report.passed is True
    assert "gc_delete" in report.scope_ids


def test_missing_gc_delete_scope_warns_or_fails_when_lifecycle_delete_required() -> None:
    policy = AuthScopePolicy(
        scopes=[
            scope
            for scope in default_auth_scope_policy().scopes
            if scope.scope_id != "gc_delete"
        ]
    )

    report = evaluate_auth_scope_policy(policy, lifecycle_delete_required=True)

    assert report.passed is False
    assert "gc_delete" in report.missing_scopes


def test_missing_gc_delete_scope_allowed_when_lifecycle_delete_not_required() -> None:
    policy = AuthScopePolicy(
        scopes=[
            scope
            for scope in default_auth_scope_policy().scopes
            if scope.scope_id != "gc_delete"
        ]
    )

    report = evaluate_auth_scope_policy(policy, lifecycle_delete_required=False)

    assert report.passed is True
    assert "gc_delete" not in report.missing_scopes
