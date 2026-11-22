# Golden path "AI service" of Socle IA: a key, an encrypted bucket, logs, a role, a budget.
# The inputs and their guardrails (validation blocks) are in variables.tf.

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}

locals {
  account_id     = data.aws_caller_identity.current.account_id
  partition      = data.aws_partition.current.partition
  region         = data.aws_region.current.region
  log_group_name = "/socle-ia/${var.service_name}"
  log_group_arn  = "arn:${local.partition}:logs:${local.region}:${local.account_id}:log-group:${local.log_group_name}"

  # The mandatory tags, set on every resource of the module that supports tags.
  tags = merge(var.tags, {
    Service            = var.service_name
    Team               = var.team
    CostCenter         = var.cost_center
    DataClassification = var.data_classification
  })
}

# --- 1. One KMS key per service, with automatic rotation ---
# TODO (step 5): a data "aws_iam_policy_document" "key" with two statements:
#   - "AccountAdministration": kms:* on "*" for the principal
#     arn:${local.partition}:iam::${local.account_id}:root (the default key policy);
#   - "CloudWatchLogsForThisLogGroup": kms:Encrypt, kms:Decrypt, kms:ReEncrypt*,
#     kms:GenerateDataKey* and kms:Describe* on "*" for the service principal
#     logs.${local.region}.amazonaws.com, with the condition ArnEquals on
#     kms:EncryptionContext:aws:logs:arn = local.log_group_arn.
# TODO (step 5): an aws_kms_key "this" (description "Key for the <service> service",
#   enable_key_rotation, rotation_period_in_days 365, deletion_window_in_days =
#   var.kms_deletion_window_days, the policy above, tags = local.tags) and an
#   aws_kms_alias "this" named "alias/${var.service_name}".

# --- 2. A private bucket, encrypted with the key, HTTPS required, versioned ---
# TODO (step 5): an aws_s3_bucket "data" (bucket_prefix "${var.service_name}-data-",
#   force_destroy = var.ephemeral, tags = local.tags), then on that bucket:
#   aws_s3_bucket_public_access_block (all four settings true),
#   aws_s3_bucket_versioning (Enabled),
#   aws_s3_bucket_server_side_encryption_configuration (sse_algorithm =
#   var.sse_algorithm, kms_master_key_id = the key ARN, bucket_key_enabled when
#   the algorithm is aws:kms), and an aws_s3_bucket_policy built from a policy
#   document "bucket" that denies s3:* to "*" on the bucket and its objects when
#   aws:SecureTransport is false (Sid DenyInsecureTransport).

# --- 3. Encrypted logs, with bounded retention ---
# TODO (step 5): an aws_cloudwatch_log_group "this" named local.log_group_name,
#   retention_in_days = var.log_retention_days, kms_key_id = the key ARN,
#   skip_destroy = !var.ephemeral, tags = local.tags.

# --- 4. A least-privilege execution role ---
# TODO (step 5): an aws_iam_role "runtime" named "${var.service_name}-runtime"
#   (description "Execution role for the <service> service", max_session_duration
#   3600, trusted by var.trusted_services) and an aws_iam_role_policy "runtime"
#   with a policy document "runtime":
#   - ListDataBucket: s3:ListBucket on the bucket ARN;
#   - ReadWriteDataObjects: s3:GetObject, s3:PutObject, s3:DeleteObject and
#     s3:AbortMultipartUpload on "<bucket ARN>/*";
#   - UseServiceKey: kms:Decrypt and kms:GenerateDataKey on the key ARN;
#   - WriteServiceLogs: logs:CreateLogStream and logs:PutLogEvents on "<log group ARN>:*";
#   - InvokeAllowedModels (dynamic, only when var.bedrock_resource_arns is not
#     empty): bedrock:InvokeModel and bedrock:InvokeModelWithResponseStream.

# --- 5. A monthly budget with actual (80%) and forecasted (100%) alerts ---
# TODO (step 5): an aws_budgets_budget "monthly" named "${var.service_name}-mensuel",
#   COST, MONTHLY, limit_amount = tostring(var.monthly_budget_usd) in USD,
#   tags = local.tags, and two notification blocks (ACTUAL GREATER_THAN 80
#   PERCENTAGE, FORECASTED GREATER_THAN 100 PERCENTAGE) sent to var.budget_email.
