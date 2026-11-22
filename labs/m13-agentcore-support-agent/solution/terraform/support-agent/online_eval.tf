# Step 10 (optional): online evaluation of every session of the runtime, with two built-in
# evaluators. Needs CloudWatch Transaction Search (scripts/enable_transaction_search.sh).
# Enable it with: terraform apply -var enable_online_eval=true

locals {
  # Conventions of the AgentCore CLI for a runtime's DEFAULT endpoint.
  runtime_log_group    = "/aws/bedrock-agentcore/runtimes/${aws_bedrockagentcore_agent_runtime.agent.agent_runtime_id}-DEFAULT"
  runtime_service_name = "${local.runtime_name}.DEFAULT"
}

resource "aws_iam_role" "online_eval" {
  count = var.enable_online_eval ? 1 : 0

  name               = "${replace(var.project_name, "_", "-")}-online-eval"
  assume_role_policy = data.aws_iam_policy_document.agentcore_trust.json
}

# Same permissions as the aws-cdk-lib OnlineEvaluationConfig construct, for built-in evaluators.
data "aws_iam_policy_document" "online_eval" {
  count = var.enable_online_eval ? 1 : 0

  statement {
    sid       = "CloudWatchLogDescribe"
    actions   = ["logs:DescribeLogGroups"]
    resources = ["*"]
  }
  statement {
    sid     = "CloudWatchLogQuery"
    actions = ["logs:StartQuery", "logs:GetQueryResults"]
    resources = [
      "arn:aws:logs:${var.region}:${local.account_id}:log-group:${local.runtime_log_group}",
      "arn:aws:logs:${var.region}:${local.account_id}:log-group:${local.runtime_log_group}:*",
      "arn:aws:logs:${var.region}:${local.account_id}:log-group:aws/spans",
      "arn:aws:logs:${var.region}:${local.account_id}:log-group:aws/spans:*",
    ]
  }
  statement {
    sid       = "CloudWatchLogWrite"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.region}:${local.account_id}:log-group:/aws/bedrock-agentcore/evaluations/*"]
  }
  statement {
    sid     = "CloudWatchIndexPolicy"
    actions = ["logs:DescribeIndexPolicies", "logs:PutIndexPolicy"]
    resources = [
      "arn:aws:logs:${var.region}:${local.account_id}:log-group:aws/spans",
      "arn:aws:logs:${var.region}:${local.account_id}:log-group:aws/spans:*",
    ]
  }
  statement {
    sid       = "CloudWatchQueryGeneration"
    actions   = ["cloudwatch:GenerateQuery", "cloudwatch:GenerateQueryResultsSummary"]
    resources = ["*"]
  }
  statement {
    sid       = "OnlineEvaluationConfig"
    actions   = ["bedrock-agentcore:GetOnlineEvaluationConfig"]
    resources = ["${local.agentcore_arn}:online-evaluation-config/${local.online_eval_name}-*"]
  }
  statement {
    sid       = "BatchEvaluation"
    actions   = ["bedrock-agentcore:StartBatchEvaluation"]
    resources = ["${local.agentcore_arn}:batch-evaluate/*"]
  }
  # Built-in evaluators run on models chosen by the service.
  statement {
    sid     = "EvaluatorModels"
    actions = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
    resources = [
      "arn:aws:bedrock:*::foundation-model/*",
      "arn:aws:bedrock:*:${local.account_id}:inference-profile/*",
    ]
  }
}

resource "aws_iam_role_policy" "online_eval" {
  count = var.enable_online_eval ? 1 : 0

  name   = "online-evaluation"
  role   = aws_iam_role.online_eval[0].id
  policy = data.aws_iam_policy_document.online_eval[0].json
}

resource "aws_bedrockagentcore_online_evaluation_config" "support_monitor" {
  count = var.enable_online_eval ? 1 : 0

  online_evaluation_config_name = local.online_eval_name
  enable_on_create              = true
  evaluation_execution_role_arn = aws_iam_role.online_eval[0].arn

  data_source_config {
    cloudwatch_logs {
      log_group_names = [local.runtime_log_group]
      service_names   = [local.runtime_service_name]
    }
  }

  evaluator {
    evaluator_id = "Builtin.Helpfulness"
  }
  evaluator {
    evaluator_id = "Builtin.GoalSuccessRate"
  }

  rule {
    sampling_config {
      sampling_percentage = 100
    }
    session_config {
      session_timeout_minutes = 5
    }
  }

  depends_on = [aws_iam_role_policy.online_eval]
}
