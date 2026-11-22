variable "region" {
  description = <<-EOT
    Region of the step 8 resources. The course default is eu-west-3 (Paris): first check on the
    Guardrails "Supported Regions" page that ApplyGuardrail is offered there; otherwise use a
    Region where it is, for example eu-west-1 (Ireland).
  EOT
  type        = string
  default     = "eu-west-3"
}

variable "prompt_attack_strength" {
  description = "Strength of the prompt attack filter on inputs: LOW, MEDIUM or HIGH."
  type        = string
  default     = "HIGH"

  validation {
    condition     = contains(["LOW", "MEDIUM", "HIGH"], var.prompt_attack_strength)
    error_message = "prompt_attack_strength must be LOW, MEDIUM or HIGH."
  }
}

# Optional, for the most advanced: D5 as an AgentCore Policy rule on the Gateway of the AgentCore
# module lab. Leave policy_engine_id null to skip it.
variable "policy_engine_id" {
  description = "Policy engine of the AgentCore lab Gateway (null: no Policy rule)."
  type        = string
  default     = null
}

variable "gateway_arn" {
  description = "ARN of the AgentCore lab Gateway the rule applies to."
  type        = string
  default     = null
}

variable "gateway_target_name" {
  description = "Name of the Gateway target that exposes the tools (the action is <target>___rembourser)."
  type        = string
  default     = "SupportTools"
}

variable "plafond_remboursement" {
  description = "Refund ceiling of the D5 rule, as PLAFOND_REMBOURSEMENT in garde.py."
  type        = number
  default     = 50
}
