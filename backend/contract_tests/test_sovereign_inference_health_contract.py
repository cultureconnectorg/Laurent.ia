"""Static contract guard: health probes must use the sovereign engine settings."""
import ast
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1] / "server.py"


def test_health_routes_use_the_sovereign_engine_environment():
    source = SERVER.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert "LAURENTIA_LOCAL_LLM_URL" in source
    assert "LAURENTIA_LOCAL_LLM_MODEL" in source
    assert "LAURENTIA_LLM_BASE_URL" not in source
    assert "from services.cvl_brain import _local_endpoint" in source
    assert "_build_client" not in source

    route_names = {
        decorator.args[0].value
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef)
        for decorator in node.decorator_list
        if isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "api_router"
        and decorator.func.attr == "get"
        and decorator.args
        and isinstance(decorator.args[0], ast.Constant)
    }
    assert "/health" in route_names
    assert "/health/inference" in route_names


def test_inference_probe_disables_redirects_and_environment_proxies():
    source = SERVER.read_text(encoding="utf-8")
    assert "follow_redirects=False" in source
    assert "trust_env=False" in source
    assert '"configured_model_not_listed"' in source
    assert '"endpoint_unreachable"' in source
