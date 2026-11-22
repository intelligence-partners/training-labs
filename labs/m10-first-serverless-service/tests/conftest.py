"""Shared fixtures: no test here talks to AWS.

LAB_TARGET selects the folder under test: "solution" (default) or "starter",
so that you can check your own work with the same tests.
"""

import importlib.util
import os
import sys
import uuid
from pathlib import Path

import pytest

LAB_DIR = Path(__file__).resolve().parent.parent
TARGET = os.environ.get("LAB_TARGET", "solution")
TARGET_DIR = LAB_DIR / TARGET

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Fake credentials and Region for moto, set before boto3 is used anywhere.
for key in ("AWS_PROFILE", "AWS_SESSION_TOKEN", "AWS_SECURITY_TOKEN"):
    os.environ.pop(key, None)
os.environ.update(
    {
        "AWS_ACCESS_KEY_ID": "testing",
        "AWS_SECRET_ACCESS_KEY": "testing",
        "AWS_DEFAULT_REGION": "eu-west-3",
        "AWS_REGION": "eu-west-3",
        "AWS_CONFIG_FILE": os.devnull,
        "AWS_SHARED_CREDENTIALS_FILE": os.devnull,
        "AWS_EC2_METADATA_DISABLED": "true",
        "TABLE_NAME": "registre-prompts",
    }
)


@pytest.fixture
def table():
    """An in-memory DynamoDB table shaped like the one in infra/main.tf."""
    import boto3
    from moto import mock_aws

    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-3")
        created = dynamodb.create_table(
            TableName=os.environ["TABLE_NAME"],
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        )
        yield created


@pytest.fixture
def app(table):
    """Load src/app.py fresh, inside the moto mock, as Lambda would on a cold start."""
    path = TARGET_DIR / "src" / "app.py"
    spec = importlib.util.spec_from_file_location(f"app_{uuid.uuid4().hex}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def plan(tmp_path_factory):
    """The JSON of an offline `terraform plan` of the target infra/ folder."""
    from tfplan import offline_plan

    return offline_plan(TARGET_DIR, "infra", tmp_path_factory.mktemp("plan"))
