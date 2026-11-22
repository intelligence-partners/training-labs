#!/usr/bin/env python3
"""Socle IA guardrail: fail if a Terraform plan creates an S3 bucket not encrypted with KMS.

Usage:
    terraform plan -out=tfplan
    terraform show -json tfplan > plan.json
    python3 guardrails/require_kms_encrypted_buckets.py plan.json
    # or: terraform show -json tfplan | python3 guardrails/require_kms_encrypted_buckets.py -

Every aws_s3_bucket of the plan, in the root module or in any module, must be
the target of an aws_s3_bucket_server_side_encryption_configuration whose
algorithm is aws:kms or aws:kms:dsse. Exit code 1 lists each faulty bucket.

Like any plan check, it only sees what goes through Terraform: a bucket created
by hand in the console escapes it. Detective controls (AWS Config) and the
absence of manual write access in production cover the other paths.
"""

import json
import re
import sys

KMS_ALGORITHMS = {"aws:kms", "aws:kms:dsse"}
MESSAGE = "Socle IA: every S3 bucket must be encrypted with a KMS key (aws:kms or aws:kms:dsse)."
INDEX = re.compile(r"\[[^\]]*\]$")


def walk(module, prefix=""):
    """Yield (module prefix, resource configuration) for the whole module tree."""
    for resource in module.get("resources", []):
        if resource.get("mode", "managed") == "managed":
            yield prefix, resource
    for name, call in module.get("module_calls", {}).items():
        yield from walk(call.get("module", {}), f"{prefix}module.{name}.")


def references(expression):
    found = []
    if isinstance(expression, dict):
        found += expression.get("references", [])
        for value in expression.values():
            found += references(value)
    elif isinstance(expression, list):
        for value in expression:
            found += references(value)
    return found


def algorithms(after):
    """SSE algorithms found in the planned value of an encryption configuration."""
    found = set()
    for rule in (after or {}).get("rule") or []:
        for default in rule.get("apply_server_side_encryption_by_default") or []:
            found.add(default.get("sse_algorithm"))
    return found


def check(plan):
    changes = {}
    for change in plan.get("resource_changes", []):
        changes.setdefault(INDEX.sub("", change["address"]), []).append(change)

    buckets = {}  # bucket address -> set of algorithms that apply to it
    encryptions = []
    for prefix, resource in walk(plan.get("configuration", {}).get("root_module", {})):
        address = prefix + resource["address"]
        if resource["type"] == "aws_s3_bucket":
            if all(c["change"]["actions"] == ["delete"] for c in changes.get(address, [])):
                continue
            buckets[address] = set()
            for c in changes.get(address, []):  # legacy inline block of aws_s3_bucket
                for block in (c["change"].get("after") or {}).get("server_side_encryption_configuration") or []:
                    buckets[address] |= algorithms(block)
        elif resource["type"] == "aws_s3_bucket_server_side_encryption_configuration":
            encryptions.append((prefix, address, resource))

    for prefix, address, resource in encryptions:
        found = set()
        for c in changes.get(address, []):
            found |= algorithms(c["change"].get("after"))
        for ref in references(resource.get("expressions", {}).get("bucket", {})):
            parts = ref.split(".")
            if parts[0] == "aws_s3_bucket" and len(parts) >= 2:
                target = f"{prefix}aws_s3_bucket.{INDEX.sub('', parts[1])}"
                if target in buckets:
                    buckets[target] |= found or {"(unknown at plan time)"}

    errors = []
    for address, found in sorted(buckets.items()):
        if found and found <= KMS_ALGORITHMS:
            print(f"  OK     {address} ({', '.join(sorted(found))})")
        else:
            detail = ", ".join(sorted(a or "none" for a in found)) or "no encryption configuration"
            errors.append(f"[Error at {address}] {MESSAGE} Found: {detail}.")
    return len(buckets), errors


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    source = sys.stdin if argv[1] == "-" else open(argv[1], encoding="utf-8")
    with source:
        plan = json.load(source)
    count, errors = check(plan)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(f"Socle IA guardrail: {len(errors)} of {count} S3 bucket(s) refused. Fix the plan before applying it.", file=sys.stderr)
        return 1
    print(f"Socle IA guardrail: {count} S3 bucket(s) checked, all encrypted with KMS.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
