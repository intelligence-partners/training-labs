"""Shared fixtures. No test reaches AWS: credentials are fake, the model is a scripted fake, and
the Gateway tools are local stand-ins."""

import importlib
import os
import pathlib
import sys

import pytest

LAB_DIR = pathlib.Path(__file__).resolve().parents[1]
SOLUTION = LAB_DIR / "solution"
STARTER = LAB_DIR / "starter"
TESTS_DIR = pathlib.Path(__file__).resolve().parent

os.environ.update(
    {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_SESSION_TOKEN": "testing",
        "AWS_DEFAULT_REGION": "eu-west-3",
        "AWS_REGION": "eu-west-3",
        "AWS_CONFIG_FILE": os.devnull,
        "AWS_SHARED_CREDENTIALS_FILE": os.devnull,
        "AWS_EC2_METADATA_DISABLED": "true",
        # Keep OpenTelemetry quiet: nothing is exported during the tests.
        "OTEL_SDK_DISABLED": "true",
    }
)
os.environ.pop("AWS_PROFILE", None)

AGENT_MODULES = ("main", "gateway_client", "memory", "memory.session")
AGENT_ENV = ("AGENTCORE_GATEWAY_TOOLS_URL", "MEMORY_AGENTMEMORY_ID", "MODEL_ID")


def agent_dir(variant):
    return variant / "SupportLab" / "app" / "agent"


@pytest.fixture
def load_agent(monkeypatch):
    """Import <variant>/SupportLab/app/agent/<module> fresh, with the given environment."""

    def _purge():
        for name in AGENT_MODULES:
            sys.modules.pop(name, None)

    def _load(module="main", variant=SOLUTION, **env):
        _purge()
        for key in AGENT_ENV:
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        monkeypatch.syspath_prepend(str(agent_dir(variant)))
        return importlib.import_module(module)

    yield _load
    _purge()


@pytest.fixture
def acme_api(monkeypatch):
    monkeypatch.setenv("API_KEY", "k" * 48)
    spec = importlib.util.spec_from_file_location("acme_api_app", SOLUTION / "acme-api" / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def http_event(method, path, api_key=None, query=None):
    """An HTTP API (payload format 2.0) event, as API Gateway sends it to the Lambda."""
    headers = {"content-type": "application/json"}
    if api_key is not None:
        headers["x-api-key"] = api_key
    return {
        "version": "2.0",
        "rawPath": path,
        "headers": headers,
        "queryStringParameters": query,
        "requestContext": {"http": {"method": method, "path": path}},
    }
