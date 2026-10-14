"""Static contract tests for truthful sovereign inference health reporting."""
import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SERVER = BACKEND / "server.py"


def test_health_reports_configured_sovereign_model_without_claiming_reachability():
    tree = ast.parse(SERVER.read_text(encoding="utf-8"), filename=str(SERVER))
    health = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "health"
    )
    source = ast.unparse(health)
    assert "LAURENTIA_LOCAL_LLM_URL" in source
    assert "LAURENTIA_LOCAL_LLM_MODEL" in source
    assert "inference_configured" in source
    assert "inference_status" in source
    assert "LAURENTIA_CLAUDE_MODEL" not in source
    assert "claude-sonnet-4-5-20250929" not in source
