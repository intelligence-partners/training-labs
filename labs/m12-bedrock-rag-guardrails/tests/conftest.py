"""Shared fixtures. Every AWS call is stubbed: the tests never reach AWS."""

import importlib.util
import os
import pathlib
import sys
import uuid

import pytest

LAB_DIR = pathlib.Path(__file__).resolve().parents[1]
SOLUTION = LAB_DIR / "solution"
STARTER = LAB_DIR / "starter"

# Fake, inert credentials and no shared config: botocore can build clients but nothing is sent.
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
    }
)
os.environ.pop("AWS_PROFILE", None)

LAMBDA_ENV = {
    "KB_ID": "KBTEST1234",
    "GUARDRAIL_ID": "gr-test-1234",
    "GUARDRAIL_VERSION": "1",
}


def load_module(path, extra_env=None, monkeypatch=None):
    """Import a file as a fresh module (module-level code reads the environment)."""
    if monkeypatch is not None:
        for key, value in (extra_env or {}).items():
            monkeypatch.setenv(key, value)
    name = f"lab_{path.stem}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def load_app(monkeypatch):
    """Load solution/lambda/app.py (or another variant) with the Lambda environment set."""

    def _load(variant=SOLUTION, **env):
        for key in ("MODEL_ID", "MODEL_EFFORT"):
            monkeypatch.delenv(key, raising=False)
        return load_module(variant / "lambda" / "app.py", {**LAMBDA_ENV, **env}, monkeypatch)

    return _load


@pytest.fixture
def index_builder():
    return load_module(SOLUTION / "index_builder" / "index_builder.py")
