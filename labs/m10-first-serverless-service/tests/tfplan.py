"""Run `terraform plan` without any AWS account and return the plan as JSON.

The configuration is copied to a temporary folder, then an override file gives
the AWS provider fake credentials, skips every account check and points every
service endpoint used by the lab at a closed local port. If the provider ever
tried to call AWS, the plan would fail instead of reaching the network.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

DEAD_ENDPOINT = "http://127.0.0.1:9"
SERVICES = ["apigatewayv2", "dynamodb", "iam", "lambda", "logs", "sts"]

OVERRIDE = """provider "aws" {
  access_key                  = "offline"
  secret_key                  = "offline"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = "true"
  skip_region_validation      = true

  endpoints {
%s
  }
}
""" % "\n".join(f'    {name} = "{DEAD_ENDPOINT}"' for name in SERVICES)

# hashicorp/setup-terraform wraps the binary and echoes the command line on stdout:
# call the real binary (terraform-bin) when it is there.
TERRAFORM = shutil.which("terraform-bin") or "terraform"

IGNORED = shutil.ignore_patterns(".terraform", ".build", "*.tfstate", "*.tfstate.*", "tfplan", "__pycache__")


def terraform_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("AWS_")}
    env.update(
        {
            "AWS_CONFIG_FILE": os.devnull,
            "AWS_SHARED_CREDENTIALS_FILE": os.devnull,
            "AWS_EC2_METADATA_DISABLED": "true",
            "TF_IN_AUTOMATION": "1",
            "CHECKPOINT_DISABLE": "1",
        }
    )
    return env


def parse_json(stdout: str) -> dict:
    """The JSON document of `terraform show -json`, ignoring any line a wrapper adds."""
    lines = [line for line in stdout.splitlines() if line.startswith("{")]
    if not lines:
        raise AssertionError(f"terraform show -json printed no JSON:\n{stdout[:2000]}")
    return json.loads(lines[-1])


def run(args, cwd):
    result = subprocess.run(args, cwd=cwd, env=terraform_env(), capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(f"{' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout


def offline_plan(project_dir: Path, workdir: str, tmp: Path, variables: dict | None = None) -> dict:
    copy = tmp / project_dir.name
    shutil.copytree(project_dir, copy, ignore=IGNORED)
    root = copy / workdir
    (root / "zz_offline_override.tf").write_text(OVERRIDE)
    var_args = [f"-var={key}={value}" for key, value in (variables or {}).items()]
    run([TERRAFORM, "init", "-backend=false", "-input=false", "-no-color"], root)
    run([TERRAFORM, "plan", "-input=false", "-refresh=false", "-lock=false", "-no-color", "-out=tfplan", *var_args], root)
    return parse_json(run([TERRAFORM, "show", "-json", "tfplan"], root))


# --- Helpers to read a plan ---------------------------------------------------


def planned(plan: dict) -> dict:
    """Planned resources by address, root module only."""
    return {r["address"]: r for r in plan["planned_values"]["root_module"].get("resources", [])}


def changes(plan: dict) -> dict:
    return {rc["address"]: rc for rc in plan["resource_changes"]}


def config(plan: dict) -> dict:
    return {r["address"]: r for r in plan["configuration"]["root_module"].get("resources", [])}


def references(expression) -> set:
    """Every reference found in a configuration expression, however nested."""
    found = set()
    if isinstance(expression, dict):
        found.update(expression.get("references", []))
        for value in expression.values():
            found |= references(value)
    elif isinstance(expression, list):
        for value in expression:
            found |= references(value)
    return found
