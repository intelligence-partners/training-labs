# Step 4: Transaction Search, required by the X-Ray OTLP endpoint for spans.
# Created only when var.enable_transaction_search is true. Destroying the destination resource
# does not change X-Ray: cleanup.sh switches it back to XRay and deletes aws/spans.

resource "aws_cloudwatch_log_resource_policy" "transaction_search" {
  count = var.enable_transaction_search ? 1 : 0

  policy_name = "m14-transaction-search"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "TransactionSearchXRayAccess"
      Effect    = "Allow"
      Principal = { Service = "xray.amazonaws.com" }
      Action    = "logs:PutLogEvents"
      Resource = [
        "arn:aws:logs:${var.region}:${local.account_id}:log-group:aws/spans:*",
        "arn:aws:logs:${var.region}:${local.account_id}:log-group:/aws/application-signals/data:*",
      ]
      Condition = {
        ArnLike      = { "aws:SourceArn" = "arn:aws:xray:${var.region}:${local.account_id}:*" }
        StringEquals = { "aws:SourceAccount" = local.account_id }
      }
    }]
  })
}

resource "aws_xray_trace_segment_destination" "cloudwatch_logs" {
  count = var.enable_transaction_search ? 1 : 0

  destination = "CloudWatchLogs"

  depends_on = [aws_cloudwatch_log_resource_policy.transaction_search]
}
