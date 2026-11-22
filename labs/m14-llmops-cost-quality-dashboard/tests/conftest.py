"""Test setup: offline, against solution/ by default (LAB_CODE_DIR=starter to point elsewhere).

No AWS credentials and no model access are needed: the Bedrock client is replaced by a mocked
Claude client, CloudWatch and Converse go through botocore's Stubber, and spans go to an
in-memory exporter.
"""
import json
import os
import sys
from pathlib import Path

import boto3
import pytest
from botocore.stub import Stubber
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

LAB = Path(__file__).resolve().parents[1]
CODE = Path(os.environ.get("LAB_CODE_DIR", LAB / "solution")).resolve()

for _var in ("MODEL_PROVIDER", "MODEL_ID", "PROMPT_VERSION", "PRICE_SHEET", "BEDROCK_CACHE_POINTS",
             "BEDROCK_STRICT_TOOLS", "BEDROCK_MAX_TOKENS", "AWS_PROFILE", "AWS_SESSION_TOKEN",
             "OTEL_TRACES_EXPORTER", "OTEL_PYTHON_DISTRO", "OTEL_PYTHON_CONFIGURATOR"):
    os.environ.pop(_var, None)
os.environ.update({"AWS_REGION": "eu-west-3", "AWS_DEFAULT_REGION": "eu-west-3",
                   "AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing"})

SPANS = InMemorySpanExporter()
_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(SPANS))
trace.set_tracer_provider(_provider)

sys.path.insert(0, str(CODE))
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture
def spans():
    SPANS.clear()
    return SPANS


def stubbed(service: str) -> boto3.client:
    """A real boto3 client whose calls are validated against the service model, then stubbed."""
    client = boto3.client(service, region_name="eu-west-3")
    client.stubber = Stubber(client)
    client.sent = []
    client.meta.events.register("provide-client-params", lambda params, **_: client.sent.append(
        json.loads(json.dumps(params))))
    client.stubber.activate()
    return client


@pytest.fixture
def cloudwatch(monkeypatch):
    import agent

    client = stubbed("cloudwatch")
    monkeypatch.setattr(agent, "cloudwatch", client)
    yield client
    client.stubber.deactivate()
