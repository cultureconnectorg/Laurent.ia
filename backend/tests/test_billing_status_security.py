"""Regression contract for checkout-status ownership."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_checkout_status_requires_authenticated_transaction_owner():
    source = (ROOT / "routes" / "billing.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    route = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_status"
    )
    calls = [
        node.func.id if isinstance(node.func, ast.Call) and isinstance(node.func.func, ast.Name)
        else node.func.attr if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        else ""
        for node in ast.walk(route)
        if isinstance(node, ast.Call)
    ]
    assert "get_current_user" in calls
    route_source = ast.unparse(route)
    assert "user_id" in route_source and "!=" in route_source
    assert route_source.index("get_current_user") < route_source.index("get_checkout_status")
    assert route_source.index("payment_transactions.find_one") < route_source.index("get_checkout_status")
