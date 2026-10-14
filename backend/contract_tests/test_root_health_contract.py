"""Static contract regression for Laurent.ia's root status endpoint."""
import ast
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1] / "server.py"


def test_root_route_is_registered_and_exposes_inference_state():
    tree = ast.parse(SERVER.read_text(encoding="utf-8"))
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
        "service",
        "status",
        "inference_configured",
        "inference_status",
        "health_url",
        "inference_readiness_url",
    } <= returned_keys


def test_root_status_does_not_claim_model_reachability():
    source = SERVER.read_text(encoding="utf-8")
    assert 'inference_status": "configured" if inference_configured else "not_configured"' in source
    assert 'inference_readiness_url": "/api/health/inference"' in source


def test_readiness_probe_uses_the_same_config_contract_as_cvl_brain():
    source = SERVER.read_text(encoding="utf-8")
    assert 'os.environ.get("LAURENTIA_LLM_BASE_URL", "").strip()' in source
    assert 'os.environ.get("LAURENTIA_LLM_MODEL", "").strip()' in source
    assert "from services.cvl_brain import _controlled_base_url" in source
    assert "_local_endpoint" not in source
    assert "LAURENTIA_LOCAL_LLM_URL" not in source
    assert "LAURENTIA_LOCAL_LLM_MODEL" not in source
