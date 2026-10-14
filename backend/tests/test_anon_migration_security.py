"""Regression contract for unverified anonymous-tenant migration."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_anon_migration_fails_closed_without_guest_ownership_proof():
    source = (ROOT / "routes" / "auth.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    route = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "migrate_anon"
    )
    route_source = ast.unparse(route)
    assert "get_current_user" in route_source
    assert "409" in route_source
    assert "update_many" not in route_source
    assert "tenant_id_for" not in route_source


def test_frontend_keeps_guest_identity_when_migration_fails():
    source = (ROOT / "frontend" / "src" / "contexts" / "AuthContext.jsx").read_text(encoding="utf-8")
    response_check = source.index("if (r.ok)", source.index("const migrateAnonIfAny"))
    removal = source.index('window.localStorage.removeItem("laurentia_anon_frek")')
    assert removal > response_check
