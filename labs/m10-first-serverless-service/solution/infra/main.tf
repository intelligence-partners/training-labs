locals {
  function_name = "${var.project_name}-prompts"
}

# --- Storage: an on-demand DynamoDB table, nothing billed without traffic ---

resource "aws_dynamodb_table" "prompts" {
  name         = var.project_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# --- Logs: the group is created here, with a 7-day retention ---

resource "aws_cloudwatch_log_group" "prompts" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 7
}

# --- Execution role: PutItem and GetItem on this table, logs in this group ---

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "prompts_function" {
  name               = "${local.function_name}-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# Two actions on this table, two on this log group, nothing else.
# No logs:CreateLogGroup: the group above already exists.
data "aws_iam_policy_document" "minimal" {
  statement {
    sid       = "RegistryTable"
    effect    = "Allow"
    actions   = ["dynamodb:PutItem", "dynamodb:GetItem"]
    resources = [aws_dynamodb_table.prompts.arn]
  }

  statement {
    sid       = "FunctionLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.prompts.arn}:*"]
  }
}

# An inline policy, and no managed policy: nothing broad is inherited.
resource "aws_iam_role_policy" "minimal" {
  name   = "${var.project_name}-minimal"
  role   = aws_iam_role.prompts_function.id
  policy = data.aws_iam_policy_document.minimal.json
}

# --- Function: Python 3.13 on Graviton (arm64), JSON logs at the INFO level ---

# The code has no dependency to package: boto3 ships with the runtime.
data "archive_file" "function" {
  type        = "zip"
  source_file = "${path.module}/../src/app.py"
  output_path = "${path.module}/.build/function.zip"
}

resource "aws_lambda_function" "prompts" {
  function_name    = local.function_name
  role             = aws_iam_role.prompts_function.arn
  runtime          = "python3.13"
  handler          = "app.handler"
  architectures    = ["arm64"]
  memory_size      = 256
  timeout          = 10
  filename         = data.archive_file.function.output_path
  source_code_hash = data.archive_file.function.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.prompts.name
    }
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.prompts.name
  }

  # The role must hold its permissions before the first invocation.
  depends_on = [aws_iam_role_policy.minimal]
}

# --- API: an HTTP API with two routes, throttled to 5 req/s (bursts of 10) ---

resource "aws_apigatewayv2_api" "prompts" {
  name          = "${var.project_name}-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.prompts.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 10
    throttling_rate_limit  = 5
  }
}

resource "aws_apigatewayv2_integration" "prompts" {
  api_id                 = aws_apigatewayv2_api.prompts.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.prompts.invoke_arn
  payload_format_version = "2.0"
}

# authorization_type NONE: the API is public. Acceptable for this throttled lab,
# deleted within the hour; a real service gets IAM, JWT or Lambda authorization.
resource "aws_apigatewayv2_route" "create_prompt" {
  api_id             = aws_apigatewayv2_api.prompts.id
  route_key          = "POST /prompts"
  target             = "integrations/${aws_apigatewayv2_integration.prompts.id}"
  authorization_type = "NONE"
}

resource "aws_apigatewayv2_route" "get_prompt" {
  api_id             = aws_apigatewayv2_api.prompts.id
  route_key          = "GET /prompts/{id}"
  target             = "integrations/${aws_apigatewayv2_integration.prompts.id}"
  authorization_type = "NONE"
}

# API Gateway may invoke the function, for these two routes of this API only.
resource "aws_lambda_permission" "create_prompt" {
  statement_id  = "AllowCreatePromptRoute"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.prompts.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.prompts.execution_arn}/*/POST/prompts"
}

resource "aws_lambda_permission" "get_prompt" {
  statement_id  = "AllowGetPromptRoute"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.prompts.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.prompts.execution_arn}/*/GET/prompts/*"
}
