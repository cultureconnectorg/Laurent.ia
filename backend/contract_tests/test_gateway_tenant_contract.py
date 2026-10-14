"""Static security contract tests for Laurentia gateway tenant boundaries."""
import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
GATEWAY = BACKEND / "routes" / "laurentia_gateway.py"


def _tree():
    return ast.parse(GATEWAY.read_text(encoding="utf-8"), filename=str(GATEWAY))


def _function(tree, name):
    return next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name
    )


def test_gateway_requires_verified_tenant_for_sensitive_routes():
    tree = _tree()
    for name in ("init_instance", "get_instance", "resolve_by_device", "get_memory", "feedback", "query"):
        source = ast.unparse(_function(tree, name))
        assert "_authorize_tenant" in source, f"{name} must enforce tenant authorization"


def test_tenant_authorizer_fails_closed_and_compares_normalized_frek_id():
    tree = _tree()
    source = ast.unparse(_function(tree, "_authorize_tenant"))
    assert "get_current_user" in source
    assert "401" in source
    assert "403" in source
    assert "strip().upper()" in source
    assert "_is_explicit_development" in source


def test_device_resolution_is_scoped_to_authenticated_frek_id():
    tree = _tree()
    source = ast.unparse(_function(tree, "resolve_by_device"))
    assert "lookup[" in source and "frek_id" in source
    assert "lookup[" in source and "device_ids" in source


def test_feedback_is_scoped_to_interaction_tenant():
    tree = _tree()
    source = ast.unparse(_function(tree, "feedback"))
    assert "tenant_id_for" in source
    assert "interaction.get('tenant_id')" in source or 'interaction.get("tenant_id")' in source
