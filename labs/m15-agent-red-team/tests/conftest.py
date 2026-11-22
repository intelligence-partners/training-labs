"""Test setup: offline, against solution/ by default (LAB_CODE_DIR=starter to point elsewhere)."""
import json
import os
import sys
from pathlib import Path

import boto3
import pytest
from botocore.stub import Stubber

LAB = Path(__file__).resolve().parents[1]
CODE = Path(os.environ.get("LAB_CODE_DIR", LAB / "solution")).resolve()
TESTS = Path(__file__).resolve().parent

for _var in ("MODEL_PROVIDER", "BEDROCK_MODEL_ID", "BEDROCK_CLASSIFIER_MODEL_ID", "BEDROCK_GUARDRAIL_ID",
             "BEDROCK_GUARDRAIL_VERSION", "BANC_AGENT", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE",
             "AWS_PROFILE", "AWS_SESSION_TOKEN"):
    os.environ.pop(_var, None)
os.environ.update({"ANTHROPIC_API_KEY": "test-key", "AWS_REGION": "eu-west-3",
                   "AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing"})

sys.path.insert(0, str(CODE))
sys.path.insert(0, str(TESTS))


@pytest.fixture
def claude(monkeypatch):
    """Scripted Claude API behind both model-facing clients (agent loop and D4 classifier)."""
    import agent
    import garde
    from fake_anthropic import FakeClaude

    fake = FakeClaude()
    monkeypatch.setattr(agent, "client", fake.client)
    monkeypatch.setattr(garde, "_client", fake.client)
    return fake


@pytest.fixture
def runtime():
    """A stubbed bedrock-runtime client; ``runtime.sent`` records the validated parameters."""
    client = boto3.client("bedrock-runtime", region_name="eu-west-3")
    client.stubber = Stubber(client)
    client.sent = []
    client.meta.events.register("provide-client-params", lambda params, **_: client.sent.append(
        json.loads(json.dumps(params))))
    client.stubber.activate()
    yield client
    client.stubber.deactivate()
