"""Static contract regression for root and sovereign inference readiness."""
import ast
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1] / "server.py"


def test_root_route_is_registered_and_exposes_inference_state():
    source = SERVER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    root_function = None
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != "root_health":
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "app"
                and decorator.func.attr == "get"
                and decorator.args
                and isinstance(decorator.args[0], ast.Constant)
                and decorator.args[0].value == "/"
            ):
                root_function = node
                break

    assert root_function is not None, "root path must have an explicit handler"
    returned_keys = {
        key.value
        for node in ast.walk(root_function)
        if isinstance(node, ast.Dict)
        for key in node.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }
    assert {
        "service", "status", "inference_configured", "inference_status",
        "health_url", "inference_readiness_url",
    } <= returned_keys


def test_health_routes_use_the_same_sovereign_engine_contract():
    source = SERVER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    health = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "health"
    )
    health_source = ast.unparse(health)
    assert "LAURENTIA_LLM_BASE_URL" in health_source
    assert "LAURENTIA_LLM_MODEL" in health_source
    assert "LAURENTIA_LOCAL_LLM_URL" not in source
    assert "LAURENTIA_LOCAL_LLM_MODEL" not in source
    assert "from services.cvl_brain import _controlled_base_url" in source
    assert "_local_endpoint" not in source
    assert "follow_redirects=False" in source
    assert "trust_env=False" in source


def test_inference_probe_disables_redirects_and_environment_proxies():
    source = SERVER.read_text(encoding="utf-8")
    assert "follow_redirects=False" in source
    assert "trust_env=False" in source
    assert '"configured_model_not_listed"' in source
    assert '"endpoint_unreachable"' in source
    assert "inference_configured" in source
    assert "inference_status" in source
