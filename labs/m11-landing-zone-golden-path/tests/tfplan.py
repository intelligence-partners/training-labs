"""Run `terraform plan` without any AWS account and return the plan as JSON.

The configuration is copied to a temporary folder, then an override file gives
the AWS provider fake credentials, skips every account check and points every
service endpoint used by the lab at a local stub. The stub answers only the two
read-only calls that the data sources make (sts:GetCallerIdentity and
sso:ListInstances) with example values; any other call gets an error, so the
plan fails instead of reaching AWS.
"""

import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ACCOUNT_ID = "111122223333"
SSO_INSTANCE_ARN = "arn:aws:sso:::instance/ssoins-0123456789abcdef"
SERVICES = ["budgets", "iam", "kms", "logs", "organizations", "s3", "ssoadmin", "sts"]

# hashicorp/setup-terraform wraps the binary and echoes the command line on stdout:
# call the real binary (terraform-bin) when it is there.
TERRAFORM = shutil.which("terraform-bin") or "terraform"

IGNORED = shutil.ignore_patterns(".terraform", "*.tfstate", "*.tfstate.*", "tfplan", "plan.json", "__pycache__")

STS_XML = f"""<GetCallerIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <GetCallerIdentityResult>
    <Arn>arn:aws:sts::{ACCOUNT_ID}:assumed-role/OfflinePlan/offline</Arn>
    <UserId>AROAOFFLINEPLAN:offline</UserId>
    <Account>{ACCOUNT_ID}</Account>
  </GetCallerIdentityResult>
  <ResponseMetadata><RequestId>00000000-0000-0000-0000-000000000000</RequestId></ResponseMetadata>
</GetCallerIdentityResponse>"""


class StubHandler(BaseHTTPRequestHandler):
    calls: list = []

    def log_message(self, *args):  # keep test output quiet
        pass

    def reply(self, status, body, content_type):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("x-amzn-RequestId", "00000000-0000-0000-0000-000000000000")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        target = self.headers.get("X-Amz-Target", "")
        self.calls.append(target or body.split("&", 1)[0])
        if "GetCallerIdentity" in body or target.endswith("GetCallerIdentity"):
            if target:  # JSON protocol
                payload = {"Account": ACCOUNT_ID, "Arn": f"arn:aws:sts::{ACCOUNT_ID}:assumed-role/OfflinePlan/offline", "UserId": "AROAOFFLINEPLAN:offline"}
                return self.reply(200, json.dumps(payload), "application/x-amz-json-1.1")
            return self.reply(200, STS_XML, "text/xml")
        if target.endswith("ListInstances"):
            payload = {"Instances": [{"InstanceArn": SSO_INSTANCE_ARN, "IdentityStoreId": "d-0123456789", "Status": "ACTIVE"}]}
            return self.reply(200, json.dumps(payload), "application/x-amz-json-1.1")
        error = {"__type": "AccessDeniedException", "message": f"offline stub: unexpected call {target or body[:80]}"}
        return self.reply(400, json.dumps(error), "application/x-amz-json-1.1")

    do_GET = do_PUT = do_DELETE = do_POST


def terraform_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("AWS_", "TF_VAR_"))}
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


def run(args, cwd, check=True):
    result = subprocess.run(args, cwd=cwd, env=terraform_env(), capture_output=True, text=True)
    if check and result.returncode != 0:
        raise AssertionError(f"{' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
    return result


class OfflineTerraform:
    """A copy of the project, wired to the local stub, ready for plan and validate."""

    def __init__(self, project_dir: Path, tmp: Path):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), StubHandler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        endpoint = f"http://127.0.0.1:{self.server.server_port}"
        self.override = """provider "aws" {
  access_key                  = "offline"
  secret_key                  = "offline"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = "true"
  skip_region_validation      = true
  s3_use_path_style           = true

  endpoints {
%s
  }
}
""" % "\n".join(f'    {name} = "{endpoint}"' for name in SERVICES)
        self.copy = tmp / project_dir.name
        shutil.copytree(project_dir, self.copy, ignore=IGNORED)
        self.initialized = set()

    def close(self):
        self.server.shutdown()

    def root(self, workdir: str) -> Path:
        root = self.copy / workdir
        if workdir not in self.initialized:
            (root / "zz_offline_override.tf").write_text(self.override)
            run([TERRAFORM, "init", "-backend=false", "-input=false", "-no-color"], root)
            self.initialized.add(workdir)
        return root

    def plan(self, workdir: str, variables: dict | None = None, check=True):
        root = self.root(workdir)
        var_args = [f"-var={key}={value}" for key, value in (variables or {}).items()]
        result = run(
            [TERRAFORM, "plan", "-input=false", "-refresh=false", "-lock=false", "-no-color", "-out=tfplan", *var_args],
            root,
            check=check,
        )
        if result.returncode != 0:
            return result
        return parse_json(run([TERRAFORM, "show", "-json", "tfplan"], root).stdout)


# --- Helpers to read a plan ---------------------------------------------------


def all_planned(plan: dict) -> dict:
    """Planned resources by full address, child modules included."""
    found = {}

    def walk(module):
        for resource in module.get("resources", []):
            found[resource["address"]] = resource
        for child in module.get("child_modules", []):
            walk(child)

    walk(plan["planned_values"]["root_module"])
    return found


def changes(plan: dict) -> dict:
    return {rc["address"]: rc for rc in plan["resource_changes"]}


def module_config(plan: dict, *path: str) -> dict:
    """Configuration of the resources of a module, by address relative to it."""
    module = plan["configuration"]["root_module"]
    for name in path:
        module = module["module_calls"][name]["module"]
    return {r["address"]: r for r in module.get("resources", [])}


def references(expression) -> set:
    found = set()
    if isinstance(expression, dict):
        found.update(expression.get("references", []))
        for value in expression.values():
            found |= references(value)
    elif isinstance(expression, list):
        for value in expression:
            found |= references(value)
    return found
