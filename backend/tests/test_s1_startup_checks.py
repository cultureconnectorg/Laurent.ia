"""S1.4 — a deployed instance refuses to start with an unsafe configuration.

Unit tests on find_problems(), then real process starts: `import server`
must exit non-zero, naming the variable but never printing its value.
"""
import os
import pathlib
import subprocess
import sys

import pytest

from services import startup_checks as sc

BACKEND = pathlib.Path(__file__).resolve().parents[1]

SAFE_PRODUCTION = {
    "APP_ENV": "production",
    "CORS_ORIGINS": "https://laurent.example",
    "LAURENTIA_ENCRYPTION_KEY": "k-" + "x" * 30,
    "LAURENTIA_SECRET_SALT": "s-" + "y" * 30,
    "LAURENTIA_ALLOWED_MODEL_HOSTS": "brain.internal",
    "BRAIN_ENGINE_URL": "http://brain.internal:8080",
}


def test_defaults_match_the_modules_that_use_them():
    for path, const, value in (
        ("services/crypto.py", "_DEFAULT_KEY", sc.DEFAULT_ENCRYPTION_KEY),
        ("services/fingerprint.py", "_DEFAULT_SALT", sc.DEFAULT_SECRET_SALT),
    ):
        assert f'{const} = "{value}"' in (BACKEND / path).read_text()


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_non_deployed_environments_are_not_checked(app_env):
    assert sc.find_problems({"APP_ENV": app_env, "EMERGENT_LLM_KEY": "x"}) == []


def test_safe_production_has_no_problem():
    assert sc.find_problems(SAFE_PRODUCTION) == []


def test_missing_app_env_is_treated_as_production():
    env = dict(SAFE_PRODUCTION)
    del env["APP_ENV"]
    env["EMERGENT_LLM_KEY"] = "x"
    assert sc.app_env(env) == "production"
    assert any("EMERGENT_LLM_KEY" in p for p in sc.find_problems(env))


def test_unknown_app_env_is_refused():
    assert sc.find_problems({**SAFE_PRODUCTION, "APP_ENV": "prod"})


@pytest.mark.parametrize("override, expected", [
    ({"EMERGENT_LLM_KEY": "x"}, "EMERGENT_LLM_KEY"),
    ({"OPENAI_API_KEY": "x"}, "OPENAI_API_KEY"),
    ({"ANTHROPIC_API_KEY": "x"}, "ANTHROPIC_API_KEY"),
    ({"SD_API_URL": "https://sd.thirdparty.example"}, "SD_API_URL"),
    ({"CVLN_MODEL_ROUTER_URL": "https://factory.example"}, "CVLN_MODEL_ROUTER_URL"),
    ({"BRAIN_ENGINE_URL": "https://api.anthropic.com"}, "BRAIN_ENGINE_URL"),
    ({"CORS_ORIGINS": "*"}, "CORS_ORIGINS"),
    ({"CORS_ORIGINS": ""}, "CORS_ORIGINS"),
    ({"LAURENTIA_ENCRYPTION_KEY": ""}, "LAURENTIA_ENCRYPTION_KEY"),
    ({"LAURENTIA_ENCRYPTION_KEY": sc.DEFAULT_ENCRYPTION_KEY}, "LAURENTIA_ENCRYPTION_KEY"),
    ({"LAURENTIA_SECRET_SALT": ""}, "LAURENTIA_SECRET_SALT"),
    ({"LAURENTIA_SECRET_SALT": sc.DEFAULT_SECRET_SALT}, "LAURENTIA_SECRET_SALT"),
])
def test_each_unsafe_setting_is_reported(override, expected):
    problems = sc.find_problems({**SAFE_PRODUCTION, **override})
    assert any(expected in p for p in problems), problems


def test_staging_is_checked_like_production():
    assert sc.find_problems({**SAFE_PRODUCTION, "APP_ENV": "staging", "EMERGENT_LLM_KEY": "x"})


def _start_server(env_overrides):
    """Import the real application in a fresh process with a clean environment."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("LAURENTIA_", "EMERGENT_", "CORS_", "APP_ENV", "SD_API", "BRAIN_ENGINE", "CVLN_"))}
    env.update({"MONGO_URL": "mongodb://127.0.0.1:27017", "DB_NAME": "startup_checks"})
    env.update(env_overrides)
    return subprocess.run([sys.executable, "-c", "import server"], cwd=BACKEND, env=env,
                          capture_output=True, text=True, timeout=120)


def test_server_refuses_to_start_with_external_llm_key_in_production():
    secret = "sk-should-never-be-printed-123"
    r = _start_server({**SAFE_PRODUCTION, "EMERGENT_LLM_KEY": secret})
    assert r.returncode != 0
    assert "EMERGENT_LLM_KEY" in r.stderr
    assert secret not in r.stderr + r.stdout


def test_server_refuses_to_start_without_app_env_and_with_public_defaults():
    r = _start_server({"CORS_ORIGINS": "*"})
    assert r.returncode != 0
    for name in ("CORS_ORIGINS", "LAURENTIA_ENCRYPTION_KEY", "LAURENTIA_SECRET_SALT"):
        assert name in r.stderr


def test_server_starts_with_a_safe_production_configuration():
    r = _start_server(SAFE_PRODUCTION)
    assert r.returncode == 0, r.stderr[-2000:]


def test_server_starts_in_test_environment():
    r = _start_server({"APP_ENV": "test"})
    assert r.returncode == 0, r.stderr[-2000:]
