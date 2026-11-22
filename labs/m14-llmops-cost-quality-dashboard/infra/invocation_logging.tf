# Step 3: Bedrock model invocation logging to CloudWatch Logs.
# Bedrock keeps a single logging configuration per account and Region: applying this file
# replaces any existing one (see the README, "Before you apply").

resource "aws_cloudwatch_log_group" "bedrock_invocations" {
  name              = "/m14/bedrock-invocations"
  retention_in_days = 7
}

resource "aws_iam_role" "bedrock_logs" {
  name = "m14-bedrock-logs"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = local.account_id }
        ArnLike      = { "aws:SourceArn" = "arn:aws:bedrock:${var.region}:${local.account_id}:*" }
      }
    }]
  })
}

resource "aws_iam_role_policy" "ecrire_journaux" {
  name = "ecrire-journaux"
  role = aws_iam_role.bedrock_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.bedrock_invocations.arn}:log-stream:aws/bedrock/modelinvocations"
    }]
  })
}

# The provider retries while the new role propagates.
resource "aws_bedrock_model_invocation_logging_configuration" "this" {
  logging_config {
    text_data_delivery_enabled      = true
    image_data_delivery_enabled     = false
    embedding_data_delivery_enabled = false

    cloudwatch_config {
      log_group_name = aws_cloudwatch_log_group.bedrock_invocations.name
      role_arn       = aws_iam_role.bedrock_logs.arn
    }
  }

  depends_on = [aws_iam_role_policy.ecrire_journaux]
}
