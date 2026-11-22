"""Test setup: offline, against solution/ by default (LAB_CODE_DIR=starter to point elsewhere)."""
import os
import shutil
import sys
from pathlib import Path

import pytest

LAB = Path(__file__).resolve().parents[1]
CODE = Path(os.environ.get("LAB_CODE_DIR", LAB / "solution")).resolve()

# No real credentials and no provider switch leak into the tests: every model call is mocked.
for _var in ("MODEL_PROVIDER", "PRICE_SHEET", "BEDROCK_MODEL_ID", "BEDROCK_CACHE_POINTS",
             "BEDROCK_STRICT_TOOLS", "BEDROCK_MAX_TOKENS", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
    os.environ.pop(_var, None)
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ.pop("AWS_PROFILE", None)
os.environ.pop("AWS_SESSION_TOKEN", None)

sys.path.insert(0, str(CODE))
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture
def lab_dir(tmp_path, monkeypatch):
    """Point tools.py and agent.py at a scratch copy of data/ so the repository stays untouched."""
    import agent
    import tools

    shutil.copytree(CODE / "data", tmp_path / "data")
    monkeypatch.setattr(tools, "ROOT", tmp_path)
    monkeypatch.setattr(tools, "DATA", tmp_path / "data")
    monkeypatch.setattr(tools, "DRAFTS", tmp_path / "drafts")
    monkeypatch.setattr(agent, "ROOT", tmp_path)
    monkeypatch.setattr(agent, "AUDIT", tmp_path / "audit.jsonl")
    return tmp_path


@pytest.fixture
def code_copy(tmp_path):
    """A scratch copy of the code folder, to run the lesson's shell commands as written."""
    target = tmp_path / "agent-tickets"
    shutil.copytree(CODE, target, ignore=shutil.ignore_patterns("__pycache__", ".venv"))
    return target
