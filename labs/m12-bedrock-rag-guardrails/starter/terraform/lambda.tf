# Step 6: the function and its execution role. The role can only query the Knowledge Base,
# invoke the inference profile and the models it routes to, apply the guardrail, and write
# its own logs.

data "aws_bedrock_inference_profile" "model" {
  inference_profile_id = var.model_id
}

locals {
  profile_arn = data.aws_bedrock_inference_profile.model.inference_profile_arn
  # The Regions a cross-Region profile routes to, read from the profile instead of hard-coded.
  destination_model_arns = [for model in data.aws_bedrock_inference_profile.model.models : model.model_arn]
}

resource "aws_iam_role" "lambda" {
  name               = "${var.lab_name}-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

data "aws_iam_policy_document" "bedrock_rag" {
  statement {
    sid       = "Retrieve"
    actions   = ["bedrock:Retrieve"]
    resources = [aws_bedrockagent_knowledge_base.this.arn]
  }
  # TODO (step 6): statement "InferenceProfile": bedrock:InvokeModel and
  # bedrock:InvokeModelWithResponseStream on local.profile_arn.

  # TODO (step 6): statement "DestinationModels": the same two actions on
  # local.destination_model_arns, only through the profile (condition StringEquals on
  # bedrock:InferenceProfileArn = local.profile_arn).

  # TODO (step 6): statement "Guardrail": bedrock:ApplyGuardrail and bedrock:GetGuardrail on
  # aws_bedrock_guardrail.this.guardrail_arn.
}

resource "aws_iam_role_policy" "bedrock_rag" {
  name   = "bedrock-rag"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.bedrock_rag.json
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.lab_name}"
  retention_in_days = var.log_retention_days
}

# Scoped replacement for the AWSLambdaBasicExecutionRole managed policy: this log group only.
data "aws_iam_policy_document" "lambda_logs" {
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.lambda.arn}:*"]
  }
}

resource "aws_iam_role_policy" "lambda_logs" {
  name   = "logs"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_logs.json
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = "${path.module}/../lambda/app.py"
  output_path = "${path.module}/build/lambda.zip"
}

resource "aws_lambda_function" "rag" {
  function_name    = var.lab_name
  role             = aws_iam_role.lambda.arn
  runtime          = "python3.12"
  handler          = "app.handler"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  timeout          = 30
  memory_size      = 512

  environment {
    variables = {
      KB_ID             = aws_bedrockagent_knowledge_base.this.id
      GUARDRAIL_ID      = aws_bedrock_guardrail.this.guardrail_id
      GUARDRAIL_VERSION = aws_bedrock_guardrail_version.v1.version
      MODEL_ID          = var.model_id
      MODEL_EFFORT      = var.model_effort
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.bedrock_rag,
    aws_iam_role_policy.lambda_logs,
  ]
}
