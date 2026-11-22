"""Shared fixtures. Every model call goes to a local fake API: no key, no network.

The tests run against solution/ by default. Set LAB_TARGET=starter to check your own
work in starter/ as you complete the TODOs.
"""

import os
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
LAB = TESTS.parent
TARGET = LAB / os.environ.get("LAB_TARGET", "solution")
HAS_PROVIDER_SWITCH = (TARGET / "bedrock.py").exists()  # the optional Bedrock path lives in solution/
sys.path.insert(0, str(TARGET))
sys.path.insert(0, str(TESTS))

from fake_api import FakeAnthropicAPI  # noqa: E402

# A tiny but well-formed one-page PDF: enough for the upload path, never parsed by the fake API.
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)

# Variables that could leak a real credential or change the code path under test.
SCRUBBED_PREFIXES = ("ANTHROPIC_", "AWS_", "BEDROCK_", "MODEL_PROVIDER", "SYNTHESE_")


@pytest.fixture(autouse=True)
def _no_real_credentials(monkeypatch):
    for name in list(os.environ):
        if name.startswith(SCRUBBED_PREFIXES):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def fake_api():
    api = FakeAnthropicAPI().start()
    yield api
    api.stop()


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """A clean working directory holding rapport.pdf, like the lesson's project folder."""
    (tmp_path / "rapport.pdf").write_bytes(MINIMAL_PDF)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def api_client(fake_api, monkeypatch):
    """Point the lab's module-level client at the fake API (real SDK, no retries)."""
    import anthropic

    import main
    import service

    client = anthropic.Anthropic(api_key="sk-ant-test", base_url=fake_api.url, max_retries=0)
    monkeypatch.setattr(service, "client", client)
    monkeypatch.setattr(main, "client", client)
    return client


def subprocess_env(**extra: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(SCRUBBED_PREFIXES)}
    env.update(extra)
    return env
