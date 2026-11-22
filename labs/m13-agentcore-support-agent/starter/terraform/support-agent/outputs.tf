output "runtime_arn" {
  description = "Runtime ARN, for agentcore invoke --runtime."
  value       = aws_bedrockagentcore_agent_runtime.agent.agent_runtime_arn
}

output "runtime_id" {
  description = "Runtime ID (last segment of the ARN), for traces, logs and evaluation."
  value       = aws_bedrockagentcore_agent_runtime.agent.agent_runtime_id
}

output "runtime_log_group" {
  description = "Log group of the runtime's DEFAULT endpoint."
  value       = local.runtime_log_group
}

output "gateway_arn" {
  description = "Gateway ARN (GATEWAY_ARN), for agentcore invoke --gateway."
  value       = aws_bedrockagentcore_gateway.tools.gateway_arn
}

output "gateway_url" {
  description = "Gateway URL, given to the runtime in AGENTCORE_GATEWAY_TOOLS_URL."
  value       = aws_bedrockagentcore_gateway.tools.gateway_url
}

output "memory_id" {
  description = "Memory ID (MEMORY_ID), for agentcore memory record list."
  value       = aws_bedrockagentcore_memory.agent_memory.id
}

output "credential_provider_arn" {
  description = "API key credential provider of the existing API."
  value       = aws_bedrockagentcore_api_key_credential_provider.acme.credential_provider_arn
}

output "policy_engine_id" {
  description = "Policy engine ID (null when enable_policy = false)."
  value       = var.enable_policy ? aws_bedrockagentcore_policy_engine.guard[0].policy_engine_id : null
}

output "online_eval_config_id" {
  description = "Online evaluation config ID (null when enable_online_eval = false)."
  value       = var.enable_online_eval ? aws_bedrockagentcore_online_evaluation_config.support_monitor[0].online_evaluation_config_id : null
}

output "online_eval_log_group" {
  description = "Log group where the service writes the evaluation results (not owned by Terraform)."
  value       = var.enable_online_eval ? try(aws_bedrockagentcore_online_evaluation_config.support_monitor[0].output_config[0].cloudwatch_config[0].log_group_name, null) : null
}

output "code_bucket" {
  description = "Bucket that holds the CodeZip artifact."
  value       = aws_s3_bucket.code.id
}
