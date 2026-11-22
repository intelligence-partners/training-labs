"""Shared fixtures: every Terraform plan here runs offline, against a local stub.

LAB_TARGET selects the folder under test: "solution" (default) or "starter",
so that you can check your own work with the same tests.
"""

import os
import sys
from pathlib import Path

import pytest

LAB_DIR = Path(__file__).resolve().parent.parent
TARGET = os.environ.get("LAB_TARGET", "solution")
TARGET_DIR = LAB_DIR / TARGET
ROOT_ID = "r-ab12"
BUDGET_EMAIL = "budget@example.com"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tfplan import OfflineTerraform  # noqa: E402


@pytest.fixture(scope="session")
def offline(tmp_path_factory):
    terraform = OfflineTerraform(TARGET_DIR, tmp_path_factory.mktemp("project"))
    yield terraform
    terraform.close()


@pytest.fixture(scope="session")
def golden_path_plan(offline):
    return offline.plan("infra/assistant-rh", {"budget_email": BUDGET_EMAIL})


@pytest.fixture(scope="session")
def landing_zone_plan(offline):
    return offline.plan("infra/landing-zone", {"root_id": ROOT_ID})


@pytest.fixture(scope="session")
def landing_zone_sso_plan(offline):
    return offline.plan("infra/landing-zone", {"root_id": ROOT_ID, "enable_identity_center": "true"})


@pytest.fixture
def scratch_project(tmp_path):
    """A fresh offline copy of the project, which a test may modify."""
    terraform = OfflineTerraform(TARGET_DIR, tmp_path)
    yield terraform
    terraform.close()
