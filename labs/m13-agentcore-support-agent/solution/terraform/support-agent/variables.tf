variable "region" {
  description = "AWS Region of the lab. Every AgentCore piece used here is available in Paris."
  type        = string
  default     = "eu-west-3"
}

variable "project_name" {
  description = "Prefix of the AgentCore resource names (lower case, letters, digits and underscores)."
  type        = string
  default     = "supportlab"

  validation {
    condition     = can(regex("^[a-z][a-z0-9_]{0,20}$", var.project_name))
    error_message = "Use lower case letters, digits and underscores, starting with a letter (21 characters at most)."
  }
}

variable "model_id" {
  description = "Model or inference profile used by the agent. AgentCore is model-agnostic: any profile whose model family is enabled in the account works."
  type        = string
  default     = "eu.anthropic.claude-opus-5-5"
}

variable "acme_api_url" {
  description = "Endpoint of the existing API (output api_url of the acme-api stack), written into the OpenAPI schema."
  type        = string

  validation {
    condition     = can(regex("^https://", var.acme_api_url))
    error_message = "The server URL must be a static https:// URL."
  }
}

variable "acme_api_key" {
  description = "Key of the existing API, stored in the AgentCore Identity token vault. Pass it with TF_VAR_acme_api_key; never commit it."
  type        = string
  sensitive   = true
}

variable "agent_zip_path" {
  description = "CodeZip artifact built by scripts/package_agent.sh."
  type        = string
  default     = null
}

variable "memory_event_expiry_days" {
  description = "Retention of the short-term memory events (7 to 365 days)."
  type        = number
  default     = 30
}

variable "enable_policy" {
  description = "Step 7: attach the Policy engine and its three Cedar policies to the Gateway, in ENFORCE mode. Use -var enable_policy=false for step 6."
  type        = bool
  default     = true
}

variable "enable_online_eval" {
  description = "Step 10 (optional): sample every session of the runtime for online evaluation."
  type        = bool
  default     = false
}
