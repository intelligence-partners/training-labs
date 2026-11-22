"""Shared fixtures for lab m07. No model download, no model call leaves the machine.

- sentence_transformers is replaced by tests/fakes/sentence_transformers (same surface,
  deterministic, no PyTorch); Chroma and rank_bm25 are the real libraries.
- Claude is replaced by a local fake API (tests/fake_api.py) reached by the real SDK.

The tests run against solution/ by default. Set LAB_TARGET=starter to check your own work.
"""

import os
import shutil
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
LAB = TESTS.parent
TARGET = LAB / os.environ.get("LAB_TARGET", "solution")
FAKES = TESTS / "fakes"
HAS_PROVIDER_SWITCH = (TARGET / "bedrock.py").exists()

SCRUBBED = ("ANTHROPIC_", "AWS_", "BEDROCK_", "MODEL_PROVIDER")
for _name in list(os.environ):
    if _name.startswith(SCRUBBED):
        del os.environ[_name]

sys.path.insert(0, str(FAKES))  # before site-packages: the fake sentence_transformers wins
sys.path.insert(0, str(TARGET))
sys.path.insert(0, str(TESTS))

from fake_api import FakeAnthropicAPI  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_chroma():
    """Chroma caches one client system per persist path, and the lab uses the relative path
    ./index: without this reset, a test would reuse the index of the previous test's folder."""
    yield
    from chromadb.api.shared_system_client import SharedSystemClient

    for system in list(SharedSystemClient._identifier_to_system.values()):
        try:
            system.stop()
        except Exception:
            pass
    SharedSystemClient.clear_system_cache()


@pytest.fixture
def fake_api():
    api = FakeAnthropicAPI().start()
    yield api
    api.stop()


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """A project folder holding corpus/, like the lesson's assistant-doc/ folder."""
    shutil.copytree(TARGET / "corpus", tmp_path / "corpus")
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def indexed(workdir):
    """Steps 3 and 5 done: chunks.jsonl and ./index exist."""
    import index
    import ingestion

    ingestion.main()
    index.main()
    return workdir


@pytest.fixture
def api_client(fake_api, monkeypatch):
    """Point the module-level clients of assistant.py and contextualiser.py at the fake API."""
    import anthropic

    import assistant
    import contextualiser

    client = anthropic.Anthropic(api_key="sk-ant-test", base_url=fake_api.url, max_retries=0)
    monkeypatch.setattr(assistant, "client", client)
    monkeypatch.setattr(contextualiser, "client", client)
    return client


def subprocess_env(**extra: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(SCRUBBED)}
    env["PYTHONPATH"] = os.pathsep.join([str(FAKES), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    env.update(extra)
    return env
