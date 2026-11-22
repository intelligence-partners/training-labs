# Step 6: the runtime "agent" (CodeZip build, no Docker): the zip built by scripts/package_agent.sh
# is uploaded to S3, and the runtime runs it with OpenTelemetry instrumentation, one microVM per
# session. The environment variables use the names the AgentCore CLI gives them.

locals {
  agent_zip = coalesce(var.agent_zip_path, "${path.module}/../../build/agent.zip")
}

data "aws_bedrock_inference_profile" "model" {
  inference_profile_id = var.model_id
}

locals {
  profile_arn            = data.aws_bedrock_inference_profile.model.inference_profile_arn
  destination_model_arns = [for model in data.aws_bedrock_inference_profile.model.models : model.model_arn]
}

resource "aws_s3_bucket" "code" {
  bucket        = "${replace(var.project_name, "_", "-")}-agent-code-${local.account_id}-${var.region}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "code" {
  bucket                  = aws_s3_bucket.code.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "code" {
  bucket = aws_s3_bucket.code.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_object" "agent_zip" {
  bucket      = aws_s3_bucket.code.id
  key         = "agent.zip"
  source      = local.agent_zip
  source_hash = fileexists(local.agent_zip) ? filemd5(local.agent_zip) : null

  lifecycle {
    precondition {
      condition     = fileexists(local.agent_zip)
      error_message = "Build the agent first: ./scripts/package_agent.sh (creates build/agent.zip)."
    }
  }

  depends_on = [aws_s3_bucket_versioning.code]
}

resource "aws_iam_role" "runtime" {
  name                 = "${replace(var.project_name, "_", "-")}-agent-runtime"
  assume_role_policy   = data.aws_iam_policy_document.agentcore_trust.json
  max_session_duration = 28800
}

data "aws_iam_policy_document" "runtime" {
  # Base permissions of a runtime (same as the aws-cdk-lib Runtime construct).
  statement {
    sid       = "LogGroupAccess"
    actions   = ["logs:DescribeLogStreams", "logs:CreateLogGroup"]
    resources = ["arn:aws:logs:${var.region}:${local.account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"]
  }
  statement {
    sid       = "DescribeLogGroups"
    actions   = ["logs:DescribeLogGroups"]
    resources = ["arn:aws:logs:${var.region}:${local.account_id}:log-group:*"]
  }
  statement {
    sid       = "LogStreamAccess"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.region}:${local.account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"]
  }
  statement {
    sid       = "XRayAccess"
    actions   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets"]
    resources = ["*"]
  }
  statement {
    sid       = "CloudWatchMetrics"
    actions   = ["cloudwatch:PutMetricData"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["bedrock-agentcore"]
    }
  }
  statement {
    sid = "GetAgentAccessToken"
    actions = [
      "bedrock-agentcore:GetWorkloadAccessToken",
      "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
      "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
    ]
    resources = [local.workload_directory_arn, "${local.workload_directory_arn}/workload-identity/*"]
  }
  statement {
    sid       = "CodeArtifact"
    actions   = ["s3:GetObject", "s3:GetObjectVersion"]
    resources = ["${aws_s3_bucket.code.arn}/${aws_s3_object.agent_zip.key}"]
  }

  # The model, only through the inference profile and the Regions it routes to.
  statement {
    sid       = "InferenceProfile"
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream", "bedrock:CountTokens"]
    resources = [local.profile_arn]
  }
  statement {
    sid       = "DestinationModels"
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream", "bedrock:CountTokens"]
    resources = local.destination_model_arns
    condition {
      test     = "StringEquals"
      variable = "bedrock:InferenceProfileArn"
      values   = [local.profile_arn]
    }
  }

  # Memory data plane (same action set as the AgentCore CLI grants), on this memory only.
  statement {
    sid = "Memory"
    actions = [
      "bedrock-agentcore:ListMemoryRecords",
      "bedrock-agentcore:RetrieveMemoryRecords",
      "bedrock-agentcore:GetEvent",
      "bedrock-agentcore:GetMemory",
      "bedrock-agentcore:GetMemoryRecord",
      "bedrock-agentcore:ListActors",
      "bedrock-agentcore:ListEvents",
      "bedrock-agentcore:ListSessions",
      "bedrock-agentcore:CreateEvent",
      "bedrock-agentcore:DeleteEvent",
      "bedrock-agentcore:DeleteMemoryRecord",
    ]
    resources = [aws_bedrockagentcore_memory.agent_memory.arn]
  }

  # SigV4 calls to the Gateway "tools" only.
  statement {
    sid       = "Gateway"
    actions   = ["bedrock-agentcore:InvokeGateway"]
    resources = [aws_bedrockagentcore_gateway.tools.gateway_arn]
  }
}

resource "aws_iam_role_policy" "runtime" {
  name   = "agent-runtime"
  role   = aws_iam_role.runtime.id
  policy = data.aws_iam_policy_document.runtime.json
}

resource "aws_bedrockagentcore_agent_runtime" "agent" {
  agent_runtime_name = local.runtime_name
  description        = "Acme support agent (lab M13)"
  role_arn           = aws_iam_role.runtime.arn

  agent_runtime_artifact {
    code_configuration {
      entry_point = ["opentelemetry-instrument", "main.py"]
      runtime     = "PYTHON_3_12"
      code {
        s3 {
          bucket     = aws_s3_bucket.code.id
          prefix     = aws_s3_object.agent_zip.key
          version_id = aws_s3_object.agent_zip.version_id
        }
      }
    }
  }

  network_configuration {
    network_mode = "PUBLIC"
  }

  protocol_configuration {
    server_protocol = "HTTP"
  }

  environment_variables = {
    MODEL_ID                    = var.model_id
    MEMORY_AGENTMEMORY_ID       = aws_bedrockagentcore_memory.agent_memory.id
    AGENTCORE_GATEWAY_TOOLS_URL = aws_bedrockagentcore_gateway.tools.gateway_url
  }

  depends_on = [
    aws_iam_role_policy.runtime,
    aws_bedrockagentcore_memory_strategy.episodic,
    aws_bedrockagentcore_gateway_target.support,
  ]
}
