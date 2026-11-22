# Step 1: the "existing API" the agent will use: a Lambda behind an HTTP API of Amazon API
# Gateway, protected by a key in the x-api-key header. In a real mission it would already exist,
# which is why it lives in its own Terraform stack.

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "acme_api" {
  name               = "acme-support-api-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

resource "aws_cloudwatch_log_group" "acme_api" {
  name              = "/aws/lambda/acme-support-api"
  retention_in_days = var.log_retention_days
}

# Scoped replacement for the AWSLambdaBasicExecutionRole managed policy: this log group only.
data "aws_iam_policy_document" "acme_api_logs" {
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.acme_api.arn}:*"]
  }
}

resource "aws_iam_role_policy" "acme_api_logs" {
  name   = "logs"
  role   = aws_iam_role.acme_api.id
  policy = data.aws_iam_policy_document.acme_api_logs.json
}

data "archive_file" "acme_api" {
  type        = "zip"
  source_file = "${path.module}/../../acme-api/app.py"
  output_path = "${path.module}/build/function.zip"
}

resource "aws_lambda_function" "acme_api" {
  function_name    = "acme-support-api"
  role             = aws_iam_role.acme_api.arn
  runtime          = "python3.13"
  handler          = "app.handler"
  filename         = data.archive_file.acme_api.output_path
  source_code_hash = data.archive_file.acme_api.output_base64sha256

  environment {
    variables = {
      API_KEY = var.acme_api_key
    }
  }

  depends_on = [aws_cloudwatch_log_group.acme_api, aws_iam_role_policy.acme_api_logs]
}

resource "aws_apigatewayv2_api" "acme_api" {
  name          = "acme-support-api"
  protocol_type = "HTTP"
  target        = aws_lambda_function.acme_api.arn
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "apigw-invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.acme_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.acme_api.execution_arn}/*"
}
