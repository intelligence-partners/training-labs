"""The plan guardrail (guardrails/require_kms_encrypted_buckets.py), on real offline plans."""

import json
import subprocess
import sys
import textwrap

from conftest import BUDGET_EMAIL, TARGET_DIR

SCRIPT = TARGET_DIR / "guardrails" / "require_kms_encrypted_buckets.py"
MESSAGE = "Socle IA: every S3 bucket must be encrypted with a KMS key"

BROUILLON = textwrap.dedent(
    """
    resource "aws_s3_bucket" "brouillon" {
      bucket_prefix = "brouillon-"
    }

    resource "aws_s3_bucket_server_side_encryption_configuration" "brouillon" {
      bucket = aws_s3_bucket.brouillon.id

      rule {
        apply_server_side_encryption_by_default {
          sse_algorithm = "AES256"
        }
      }
    }
    """
)


def guardrail(plan):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "-"], input=json.dumps(plan), capture_output=True, text=True
    )


def test_golden_path_passes_the_guardrail(golden_path_plan):
    result = guardrail(golden_path_plan)
    assert result.returncode == 0, result.stderr
    assert "module.assistant_rh.aws_s3_bucket.data (aws:kms)" in result.stdout
    assert "1 S3 bucket(s) checked, all encrypted with KMS." in result.stdout


def test_landing_zone_has_no_bucket(landing_zone_plan):
    result = guardrail(landing_zone_plan)
    assert result.returncode == 0
    assert "0 S3 bucket(s) checked" in result.stdout


def test_brouillon_bucket_encrypted_by_s3_is_refused(scratch_project):
    """Step 10: a bucket added next to the golden path, encrypted with SSE-S3."""
    main = scratch_project.copy / "infra" / "assistant-rh" / "main.tf"
    main.write_text(main.read_text() + BROUILLON)
    plan = scratch_project.plan("infra/assistant-rh", {"budget_email": BUDGET_EMAIL})

    result = guardrail(plan)

    assert result.returncode == 1
    assert f"[Error at aws_s3_bucket.brouillon] {MESSAGE}" in result.stderr
    assert "Found: AES256." in result.stderr
    assert "module.assistant_rh.aws_s3_bucket.data (aws:kms)" in result.stdout


def test_bucket_without_any_encryption_configuration_is_refused(scratch_project):
    main = scratch_project.copy / "infra" / "assistant-rh" / "main.tf"
    main.write_text(main.read_text() + 'resource "aws_s3_bucket" "brouillon" {\n  bucket_prefix = "brouillon-"\n}\n')
    plan = scratch_project.plan("infra/assistant-rh", {"budget_email": BUDGET_EMAIL})

    result = guardrail(plan)

    assert result.returncode == 1
    assert "Found: no encryption configuration." in result.stderr


def test_script_reads_a_file_and_checks_its_arguments(golden_path_plan, tmp_path):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(golden_path_plan))
    assert subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True).returncode == 0
    assert subprocess.run([sys.executable, str(SCRIPT)], capture_output=True).returncode == 2
