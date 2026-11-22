# Step 8, optional: D5 as a Cedar rule evaluated by AgentCore Policy at the Gateway, outside the
# agent's code. Deploy the policy engine in LOG_ONLY mode on the Gateway first, then ENFORCE
# (that mode belongs to the AgentCore lab's Gateway configuration, not to this rule).

resource "aws_bedrockagentcore_policy" "plafond_remboursement" {
  count = var.policy_engine_id == null ? 0 : 1

  name             = "m15_plafond_remboursement"
  description      = "M15 lab: refuse rembourser above the refund ceiling."
  policy_engine_id = var.policy_engine_id

  definition {
    cedar {
      statement = templatefile("${path.module}/policy-rembourser.cedar.tftpl", {
        gateway_arn           = var.gateway_arn
        gateway_target_name   = var.gateway_target_name
        plafond_remboursement = var.plafond_remboursement
      })
    }
  }

  lifecycle {
    precondition {
      condition     = var.gateway_arn != null
      error_message = "Set gateway_arn together with policy_engine_id."
    }
  }
}
