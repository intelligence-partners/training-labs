# Steps 3 and 4: the Gateway "tools", authenticated with IAM (SigV4), and its OpenAPI target
# "support". Each operationId becomes a tool named support___<operationId>.

locals {
  # Step 3: the server URL must be static, so the real API URL replaces the "API_URL" placeholder
  # of the template.
  openapi_template = jsondecode(file("${local.project_dir}/schemas/acme-support.template.json"))
  openapi_schema   = merge(local.openapi_template, { servers = [{ url = var.acme_api_url }] })
}

resource "aws_iam_role" "gateway" {
  name               = "${local.gateway_name}-gateway"
  assume_role_policy = data.aws_iam_policy_document.agentcore_trust.json
}

# What the Gateway needs to present the API key: its workload identity token, the key from the
# token vault, and the secret that holds it.
data "aws_iam_policy_document" "gateway" {
  statement {
    sid     = "WorkloadIdentity"
    actions = ["bedrock-agentcore:GetWorkloadAccessToken"]
    resources = [
      local.workload_directory_arn,
      "${local.workload_directory_arn}/workload-identity/${local.gateway_name}-*",
    ]
  }
  statement {
    sid     = "ApiKey"
    actions = ["bedrock-agentcore:GetResourceApiKey"]
    resources = [
      "${local.agentcore_arn}:token-vault/default",
      aws_bedrockagentcore_api_key_credential_provider.acme.credential_provider_arn,
      local.workload_directory_arn,
      "${local.workload_directory_arn}/workload-identity/${local.gateway_name}-*",
    ]
  }
  statement {
    sid       = "ApiKeySecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_bedrockagentcore_api_key_credential_provider.acme.api_key_secret_arn[0].secret_arn]
  }
}

resource "aws_iam_role_policy" "gateway" {
  name   = "outbound-api-key"
  role   = aws_iam_role.gateway.id
  policy = data.aws_iam_policy_document.gateway.json
}

resource "aws_bedrockagentcore_gateway" "tools" {
  name            = local.gateway_name
  role_arn        = aws_iam_role.gateway.arn
  authorizer_type = "AWS_IAM"
  protocol_type   = "MCP"

  # Step 7: every tool call is decided by the Policy engine.
  dynamic "policy_engine_configuration" {
    for_each = var.enable_policy ? [aws_bedrockagentcore_policy_engine.guard[0].policy_engine_arn] : []
    content {
      arn  = policy_engine_configuration.value
      mode = "ENFORCE"
    }
  }
}

resource "aws_bedrockagentcore_gateway_target" "support" {
  name               = "support"
  gateway_identifier = aws_bedrockagentcore_gateway.tools.gateway_id

  credential_provider_configuration {
    api_key {
      provider_arn              = aws_bedrockagentcore_api_key_credential_provider.acme.credential_provider_arn
      credential_location       = "HEADER"
      credential_parameter_name = "x-api-key"
    }
  }

  target_configuration {
    mcp {
      open_api_schema {
        inline_payload {
          payload = jsonencode(local.openapi_schema)
        }
      }
    }
  }

  depends_on = [aws_iam_role_policy.gateway]
}
