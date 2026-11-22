# Golden path "AI service" of Socle IA: a key, an encrypted bucket, logs, a role, a budget.

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

data "aws_iam_policy_document" "key" {
  # The default key policy: the account administers the key through IAM.
  statement {
    sid       = "AccountAdministration"
    actions   = ["kms:*"]
    resources = ["*"]

    principals {
      type        = "AWS"
      identifiers = ["arn:${local.partition}:iam::${local.account_id}:root"]
    }
  }

  # CloudWatch Logs may use the key, for this log group only.
  statement {
    sid       = "CloudWatchLogsForThisLogGroup"
    actions   = ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:Describe*"]
    resources = ["*"]

    principals {
      type        = "Service"
      identifiers = ["logs.${local.region}.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "kms:EncryptionContext:aws:logs:arn"
      values   = [local.log_group_arn]
    }
  }
}

resource "aws_kms_key" "this" {
  description             = "Key for the ${var.service_name} service"
  enable_key_rotation     = true
  rotation_period_in_days = 365
  deletion_window_in_days = var.kms_deletion_window_days
  policy                  = data.aws_iam_policy_document.key.json
  tags                    = local.tags
}

resource "aws_kms_alias" "this" {
  name          = "alias/${var.service_name}"
  target_key_id = aws_kms_key.this.key_id
}

# --- 2. A private bucket, encrypted with the key, HTTPS required, versioned ---

resource "aws_s3_bucket" "data" {
  bucket_prefix = "${var.service_name}-data-"
  # Lab (ephemeral): destroy empties the bucket, every version included.
  force_destroy = var.ephemeral
  tags          = local.tags
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.sse_algorithm
      kms_master_key_id = aws_kms_key.this.arn
    }
    # Fewer calls to KMS, so a lower cost. S3 Bucket Keys do not apply to DSSE-KMS.
    bucket_key_enabled = var.sse_algorithm == "aws:kms"
  }
}

data "aws_iam_policy_document" "bucket" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.data.arn, "${aws_s3_bucket.data.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "data" {
  bucket = aws_s3_bucket.data.id
  policy = data.aws_iam_policy_document.bucket.json

  depends_on = [aws_s3_bucket_public_access_block.data]
}

# --- 3. Encrypted logs, with bounded retention ---

resource "aws_cloudwatch_log_group" "this" {
  name              = local.log_group_name
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.this.arn
  # Outside a lab, destroy leaves the log group (and its logs) in place.
  skip_destroy = !var.ephemeral
  tags         = local.tags
}

# --- 4. A least-privilege execution role ---

data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = var.trusted_services
    }
  }
}

resource "aws_iam_role" "runtime" {
  name                 = "${var.service_name}-runtime"
  description          = "Execution role for the ${var.service_name} service"
  assume_role_policy   = data.aws_iam_policy_document.assume_role.json
  max_session_duration = 3600
  tags                 = local.tags
}

data "aws_iam_policy_document" "runtime" {
  statement {
    sid       = "ListDataBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn]
  }

  statement {
    sid       = "ReadWriteDataObjects"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload"]
    resources = ["${aws_s3_bucket.data.arn}/*"]
  }

  # SSE-KMS: GenerateDataKey to write an object, Decrypt to read it.
  statement {
    sid       = "UseServiceKey"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [aws_kms_key.this.arn]
  }

  statement {
    sid       = "WriteServiceLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.this.arn}:*"]
  }

  dynamic "statement" {
    for_each = length(var.bedrock_resource_arns) > 0 ? [var.bedrock_resource_arns] : []

    content {
      sid       = "InvokeAllowedModels"
      actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
      resources = statement.value
    }
  }
}

resource "aws_iam_role_policy" "runtime" {
  name   = "${var.service_name}-runtime"
  role   = aws_iam_role.runtime.id
  policy = data.aws_iam_policy_document.runtime.json
}

# --- 5. A monthly budget with actual (80%) and forecasted (100%) alerts ---

resource "aws_budgets_budget" "monthly" {
  name         = "${var.service_name}-mensuel"
  budget_type  = "COST"
  time_unit    = "MONTHLY"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  tags         = local.tags

  notification {
    notification_type          = "ACTUAL"
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.budget_email]
  }

  notification {
    notification_type          = "FORECASTED"
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    subscriber_email_addresses = [var.budget_email]
  }
}
