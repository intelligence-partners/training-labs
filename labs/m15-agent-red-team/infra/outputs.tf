output "guardrail_id" {
  description = "Export it as BEDROCK_GUARDRAIL_ID for the guardrail defense."
  value       = aws_bedrock_guardrail.prompt_attack.guardrail_id
}

output "guardrail_arn" {
  value = aws_bedrock_guardrail.prompt_attack.guardrail_arn
}

output "region" {
  value = var.region
}

output "policy_id" {
  value = one(aws_bedrockagentcore_policy.plafond_remboursement[*].policy_id)
}
