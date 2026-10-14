import ast
from pathlib import Path


def test_stream_uses_incremental_completion_api():
    path = Path(__file__).resolve().parents[1] / "services" / "cvl_brain.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == "chat_stream")
    source = ast.unparse(fn)
    assert "stream=True" in source
    assert "async for event in stream" in source
    assert "await client.close()" in source
    assert "await chat_enriched" not in source
