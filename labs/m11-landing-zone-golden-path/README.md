# M11 lab: a landing zone and a golden path

Companion code for the lab of module M11 (platform engineering) of Intelligence Training. Version française : [README.fr.md](README.fr.md).

The infrastructure is written in **Terraform** (HCL), with the `hashicorp/aws` provider pinned to an exact version. The golden path is a reusable Terraform **module** whose tags and guardrails are variables.

## Goal and architecture

Everything is deployed into the **management account** of a test organization, Region `eu-west-3` (Organizations is global). In production, the `assistant-rh` service would go into a member account `assistant-rh-dev` and the management account would host no workload, as the multi-account lesson recommends.

- **Landing zone** (`infra/landing-zone`): six OUs (Security, Infrastructure, Sandbox, Workloads, plus Dev and Prod under Workloads) and four SCPs: `DenyLeaveOrganization` on the root, `DenyOutsideAllowedRegions` on the four top-level OUs (not the root, so that you can test it without risk), `ProtectSecurityBaseline` on Infrastructure, Sandbox and Workloads (not Security, where the security team administers these services), `DenyIamUsers` on Sandbox and Workloads. The `SoclePlatformAdmin` role is exempt from the protection SCPs. Optional: the permission sets of the Identity Center lesson's catalog (`enable_identity_center`).
- **Golden path** (`infra/modules/ai-service-baseline`), called by `infra/assistant-rh`: a KMS key with rotation (`alias/assistant-rh`), an S3 bucket encrypted with that key, private, versioned and reachable over HTTPS only, a log group `/socle-ia/assistant-rh` encrypted with the key and kept 30 days, a least-privilege execution role `assistant-rh-runtime`, and a monthly budget `assistant-rh-mensuel` (20 USD, alerts at 80% actual and 100% forecasted). Every resource carries the four mandatory tags `Service`, `Team`, `CostCenter`, `DataClassification`.
- **Guardrails**, at two levels: the module's variables only accept compliant values (`sse_algorithm` must be `aws:kms` or `aws:kms:dsse`, bounded log retention, 7 to 30-day key deletion window, explicit Bedrock ARNs), and `guardrails/require_kms_encrypted_buckets.py` refuses a Terraform plan that creates **any** S3 bucket not encrypted with KMS, inside or outside the golden path.

```
labs/m11-landing-zone-golden-path/
├── starter/                         what you start from (the socle-ia project, with TODOs)
├── solution/                        the complete, working project
│   ├── infra/
│   │   ├── landing-zone/            providers.tf, variables.tf, main.tf, identity-center.tf, outputs.tf
│   │   ├── assistant-rh/            providers.tf, variables.tf, main.tf, outputs.tf
│   │   └── modules/ai-service-baseline/   versions.tf, variables.tf, main.tf, outputs.tf
│   └── guardrails/require_kms_encrypted_buckets.py
├── tests/                           offline terraform plans (local stub) and guardrail tests
├── test.sh                          runs every offline check
├── cleanup.sh                       destroys both root modules, in the lesson's order
└── .env.example
```

## Prerequisites

- An **AWS account dedicated to training**, which belongs to no corporate organization. It becomes the management account of a test organization. Never run this lab in the management account of your company's organization.
- Administrator access to this account, ideally through IAM Identity Center or a role, with MFA, in a CLI profile.
- **AWS CLI v2**, **Terraform 1.5.7 or later**, **Python 3.10 or later** (for the guardrail) and `git`. Terraform downloads `hashicorp/aws` 6.72.0 on `terraform init`.
- An email address for the budget alerts.
- Optional: IAM Identity Center enabled for the organization, to create the permission sets.

## Estimated cost

As the lesson states it: Organizations, OUs and SCPs are free; the customer managed KMS key costs around $1 per month, prorated hourly, so less than one cent for a few hours, and is not billed during the pending deletion period; the S3 bucket and the log group cost a few cents at most, often covered by the free tier; the AWS Budgets budget is free. The lab costs **less than $0.10** if you clean up the same day. Prices change: check the KMS and Budgets pricing pages. (The lesson's lines on the cleanup Lambda function and the CDKToolkit stack do not apply to the Terraform version: neither exists.)

## Steps (mapped to the lesson)

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m11-landing-zone-golden-path/starter   # or solution/ to deploy the finished lab
```

| Lesson step | In this repo |
| --- | --- |
| 1. Prepare the test organization | the lesson's CLI commands (create the organization, `enable-policy-type`), then `export TF_VAR_root_id=$ROOT_ID TF_VAR_budget_email=$BUDGET_EMAIL` |
| 2. Create the project | `starter/` is the `socle-ia` project; `terraform version` must show 1.5.7 or later |
| 3. Prepare the account | no bootstrap with Terraform: `terraform -chdir=infra/landing-zone init` and `terraform -chdir=infra/assistant-rh init` |
| 4. The simplified landing zone | `infra/landing-zone/main.tf` (TODOs: Dev and Prod OUs, three SCPs) and `outputs.tf` |
| 5. The "AI service" golden path | `infra/modules/ai-service-baseline/main.tf` and `outputs.tf`, then the call in `infra/assistant-rh/main.tf` and `outputs.tf` |
| 6. The guardrail | `guardrails/require_kms_encrypted_buckets.py` (TODO in `check()`); the module's `variables.tf` holds the input guardrails |
| 7. Plan and review | `terraform plan` of both root modules, then the guardrail on the golden path's plan |
| 8. Deploy the landing zone | `terraform -chdir=infra/landing-zone apply` (20 resources), then the lesson's checks |
| 9. Deploy the golden path | `terraform -chdir=infra/assistant-rh apply tfplan` (11 resources), then the lesson's checks |
| 10. Verify the guardrail | add the `brouillon` bucket below, plan, run the guardrail: it fails; then remove it |
| Cleanup | `bash cleanup.sh` (see below) |

## Deploy

From the project folder (`starter/` once completed, or `solution/`):

```bash
export AWS_PROFILE=formation AWS_REGION=eu-west-3
aws sts get-caller-identity
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export BUDGET_EMAIL=you@example.com
# Step 1: create the organization if needed, enable SCPs (see the lesson)
export ROOT_ID=$(aws organizations list-roots --query 'Roots[0].Id' --output text)
export TF_VAR_root_id=$ROOT_ID TF_VAR_budget_email=$BUDGET_EMAIL

# Steps 3 and 7: init, plan, review
terraform -chdir=infra/landing-zone init
terraform -chdir=infra/assistant-rh init
terraform -chdir=infra/landing-zone plan
terraform -chdir=infra/assistant-rh plan -out=tfplan
terraform -chdir=infra/assistant-rh show -json tfplan > plan.json
python3 guardrails/require_kms_encrypted_buckets.py plan.json
#   Socle IA guardrail: 1 S3 bucket(s) checked, all encrypted with KMS.

# Step 8: the landing zone
terraform -chdir=infra/landing-zone apply
aws organizations list-organizational-units-for-parent --parent-id $ROOT_ID --query 'OrganizationalUnits[].Name'
aws organizations list-policies --filter SERVICE_CONTROL_POLICY --query 'Policies[].Name' --output text

# Step 9: the golden path
terraform -chdir=infra/assistant-rh apply tfplan
export BUCKET=$(terraform -chdir=infra/assistant-rh output -raw bucket_name)
export KEY_ID=$(terraform -chdir=infra/assistant-rh output -raw kms_key_id)
aws s3api get-bucket-encryption --bucket $BUCKET
aws kms get-key-rotation-status --key-id $KEY_ID
aws logs describe-log-groups --log-group-name-prefix /socle-ia/ --query 'logGroups[].[logGroupName,retentionInDays,kmsKeyId]'
aws budgets describe-budgets --account-id $ACCOUNT_ID --query 'Budgets[].[BudgetName,BudgetLimit.Amount,BudgetLimit.Unit]'
```

In the plan of `infra/assistant-rh`, find the key policy (the `CloudWatchLogsForThisLogGroup` statement allows `logs.eu-west-3.amazonaws.com`, for the `/socle-ia/assistant-rh` log group only), the bucket policy that denies requests without TLS (`aws:SecureTransport` = `false`) and the four tags on the budget.

Step 10: add temporarily to `infra/assistant-rh/main.tf`

```hcl
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
```

then plan and run the guardrail again: it exits with code 1 and prints `[Error at aws_s3_bucket.brouillon] Socle IA: every S3 bucket must be encrypted with a KMS key (aws:kms or aws:kms:dsse). Found: AES256.` Passing `sse_algorithm = "AES256"` to the module fails even earlier, at `terraform validate`, with the same message. Remove the `brouillon` bucket afterwards.

## Test (offline)

```bash
bash test.sh                      # the solution
LAB_TARGET=starter bash test.sh   # your work in starter/ (fails until every TODO is done)
```

`test.sh` needs no AWS account and makes no AWS call. It creates `.venv`, then runs `terraform fmt -check -recursive`, `terraform init -backend=false` and `terraform validate` on the three Terraform folders of `solution/` and `starter/`, then the tests in `tests/`. These run real `terraform plan` commands with fake credentials, every AWS endpoint pointed at a local stub that only answers `sts:GetCallerIdentity` and `sso:ListInstances` with example values, and assert:

- the six OUs and their parents, the exact JSON of the four SCPs, their targets (only `DenyLeaveOrganization` on the root, no `ProtectSecurityBaseline` on Security), their size under 5,120 characters, and the optional permission sets;
- for the golden path: key rotation, 7-day deletion window, key policy, bucket encryption with the key and Bucket Key, public access block, versioning, TLS-only bucket policy, 30-day encrypted log group, the exact actions and resources of the execution role, the budget and its alerts, the four tags on every resource;
- the module's guardrails (non-KMS encryption, retention, deletion window, service name, classification) and the plan guardrail on the `brouillon` bucket.

What only a real deployment can verify: that Organizations accepts the SCPs and their attachments, that CloudWatch Logs accepts the key for the encrypted log group, the effect of the SCPs on a member account, and the budget email.

## Clean up

```bash
bash cleanup.sh                          # steps 1 to 3 of the lesson's cleanup
bash cleanup.sh --disable-scp            # also disables the SCP policy type on the root
bash cleanup.sh --delete-organization    # also deletes the organization if it has no member account
bash cleanup.sh --yes                    # without Terraform's confirmation prompts
```

In order: `terraform destroy` of `infra/assistant-rh` (the bucket is emptied, every version included, the log group and the budget are deleted, the key enters a 7-day `PendingDeletion`, which the script checks), then `terraform destroy` of `infra/landing-zone` (attachments, SCPs, then the empty OUs; the script checks that no OU is left under the root). What Terraform does not own, because step 1 created it with the CLI, is optional: the SCP policy type and the organization itself.
