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

Starter file for step 6: complete check(). The helpers below are given.
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
    """Every reference (for example aws_s3_bucket.data.id) in a configuration expression."""
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
    """Return (number of buckets checked, list of error messages)."""
    # TODO (step 6):
    #   1. Index plan["resource_changes"] by address, without the [index] suffix
    #      (INDEX.sub("", address)).
    #   2. With walk(plan["configuration"]["root_module"]), list every
    #      aws_s3_bucket (full address = prefix + resource["address"]) that is not
    #      only being deleted, and every
    #      aws_s3_bucket_server_side_encryption_configuration.
    #   3. For each encryption configuration, read its algorithms from the planned
    #      value (algorithms(change["change"]["after"])) and attach them to the
    #      bucket its "bucket" expression references (aws_s3_bucket.<name>).
    #   4. Each bucket whose algorithms are not all in KMS_ALGORITHMS (or that has
    #      none) gives the error f"[Error at {address}] {MESSAGE} Found: ...".
    return 0, []


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
