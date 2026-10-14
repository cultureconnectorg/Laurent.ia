"""Static contract regression tests for the Meta CVLN briefing compatibility route.

These checks intentionally use only the Python standard library so they can run
without importing the production application or connecting to MongoDB.
The test is intentionally isolated from production secrets and external services.
"""
import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SERVER = BACKEND / "server.py"
BRAIN = BACKEND / "routes" / "brain.py"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_server_registers_post_briefing_alias_to_existing_handler():
    tree = _tree(SERVER)
    imports_briefing = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "routes.brain"
        and any(alias.name == "briefing" and alias.asname == "brain_briefing" for alias in node.names)
        for node in ast.walk(tree)
    )
    assert imports_briefing, "server must import the existing protected briefing handler"

    alias_registered = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "app":
            continue
        if node.func.attr != "add_api_route" or not node.args:
            continue
        if not isinstance(node.args[0], ast.Constant) or node.args[0].value != "/api/briefing":
            continue
        if len(node.args) < 2 or not isinstance(node.args[1], ast.Name) or node.args[1].id != "brain_briefing":
            continue
        methods = next((kw.value for kw in node.keywords if kw.arg == "methods"), None)
        if isinstance(methods, ast.List) and [
            elt.value for elt in methods.elts if isinstance(elt, ast.Constant)
        ] == ["POST"]:
            alias_registered = True
            break

    assert alias_registered, "POST /api/briefing must point to the existing briefing handler"


def test_briefing_handler_keeps_interservice_authentication():
    tree = _tree(BRAIN)
    handler = next(
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "briefing"
    )
    source = ast.unparse(handler)
    assert "X-API-Key" in source
    assert "LAURENTIA_CVLN_SERVICE_API_KEY" in source
    assert "hmac.compare_digest" in source
    assert "HTTPException(403" in source
