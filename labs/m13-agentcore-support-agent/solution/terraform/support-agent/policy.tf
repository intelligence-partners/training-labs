# Step 7: the refund rule lives in Policy, not in the prompt. The engine "guard" is attached to
# the Gateway in ENFORCE mode (gateway.tf) and holds three Cedar policies. The service validates
# each policy against the tool schema of the Gateway, hence the dependency on the target.

locals {
  policies_dir = "${local.project_dir}/policies"
  # Policy name => template file. The templates keep the GATEWAY_ARN placeholder of the lesson.
  cedar_policies = {
    LectureEtTickets      = "lecture.template.cedar"
    RemboursementPlafonne = "remboursement.template.cedar"
    PasDeRemboursementB2B = "b2b.template.cedar"
  }
}

resource "aws_bedrockagentcore_policy_engine" "guard" {
  count = var.enable_policy ? 1 : 0

  name        = local.policy_engine_name
  description = "Acme support: reads and tickets allowed, refunds capped at 5000 cents, no B2B refund"
}

resource "aws_bedrockagentcore_policy" "rules" {
  for_each = var.enable_policy ? local.cedar_policies : {}

  name             = each.key
  policy_engine_id = aws_bedrockagentcore_policy_engine.guard[0].policy_engine_id
  validation_mode  = "FAIL_ON_ANY_FINDINGS"

  definition {
    cedar {
      statement = replace(file("${local.policies_dir}/${each.value}"), "GATEWAY_ARN", aws_bedrockagentcore_gateway.tools.gateway_arn)
    }
  }

  depends_on = [aws_bedrockagentcore_gateway_target.support]
}

# The Gateway asks the engine for a decision on every tool call (same grant as the AgentCore CLI).
data "aws_iam_policy_document" "gateway_policy_engine" {
  count = var.enable_policy ? 1 : 0

  statement {
    sid = "PolicyEngine"
    actions = [
      "bedrock-agentcore:GetPolicyEngine",
      "bedrock-agentcore:CheckAuthorizePermissions",
      "bedrock-agentcore:AuthorizeAction",
      "bedrock-agentcore:PartiallyAuthorizeActions",
    ]
    resources = [
      aws_bedrockagentcore_policy_engine.guard[0].policy_engine_arn,
      aws_bedrockagentcore_gateway.tools.gateway_arn,
    ]
  }
  statement {
    sid       = "GuardrailChecks"
    actions   = ["bedrock:InvokeGuardrailChecks"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "gateway_policy_engine" {
  count = var.enable_policy ? 1 : 0

  name   = "policy-engine"
  role   = aws_iam_role.gateway.id
  policy = data.aws_iam_policy_document.gateway_policy_engine[0].json
}
