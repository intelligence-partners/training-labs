locals {
  function_name = "${var.project_name}-prompts"
}

# --- Storage: an on-demand DynamoDB table, nothing billed without traffic ---
# Given as an example of the resource syntax.

resource "aws_dynamodb_table" "prompts" {
  name         = var.project_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# --- Logs ---
# TODO (step 2): an aws_cloudwatch_log_group "prompts" named
#   "/aws/lambda/${local.function_name}", kept 7 days (retention_in_days).

# --- Execution role ---
# TODO (step 2): a data "aws_iam_policy_document" "lambda_assume_role" that lets
#   the lambda.amazonaws.com service call sts:AssumeRole, and an
#   aws_iam_role "prompts_function" named "${local.function_name}-role" using it.
# TODO (step 2): a data "aws_iam_policy_document" "minimal" with two statements:
#   - sid "RegistryTable": dynamodb:PutItem and dynamodb:GetItem on
#     aws_dynamodb_table.prompts.arn only;
#   - sid "FunctionLogs": logs:CreateLogStream and logs:PutLogEvents on
#     "${aws_cloudwatch_log_group.prompts.arn}:*" only.
#   No logs:CreateLogGroup, no wildcard action, no managed policy.
# TODO (step 2): an aws_iam_role_policy "minimal" named "${var.project_name}-minimal"
#   that attaches this document to the role.

# --- Function ---
# The code has no dependency to package: boto3 ships with the runtime.
data "archive_file" "function" {
  type        = "zip"
  source_file = "${path.module}/../src/app.py"
  output_path = "${path.module}/.build/function.zip"
}

# TODO (step 2): an aws_lambda_function "prompts" named local.function_name:
#   runtime python3.13, handler app.handler, architectures ["arm64"],
#   memory_size 256, timeout 10, the role above, the zip above
#   (filename and source_code_hash = output_base64sha256), the environment
#   variable TABLE_NAME, and a logging_config block: log_format JSON,
#   application_log_level and system_log_level INFO, log_group = the group above.
#   Add depends_on = [aws_iam_role_policy.minimal].

# --- API ---
# TODO (step 2): an aws_apigatewayv2_api "prompts" (protocol_type HTTP), an
#   aws_apigatewayv2_stage "default" named "$default" with auto_deploy and
#   default_route_settings throttled to 5 requests per second, bursts of 10.
# TODO (step 2): an aws_apigatewayv2_integration "prompts" (AWS_PROXY, POST,
#   the function's invoke_arn, payload_format_version "2.0") and two
#   aws_apigatewayv2_route: "POST /prompts" (create_prompt) and
#   "GET /prompts/{id}" (get_prompt), authorization_type NONE.
# TODO (step 2): two aws_lambda_permission that let apigateway.amazonaws.com
#   invoke the function, with source_arn
#   "${aws_apigatewayv2_api.prompts.execution_arn}/*/POST/prompts" and
#   "${aws_apigatewayv2_api.prompts.execution_arn}/*/GET/prompts/*".
