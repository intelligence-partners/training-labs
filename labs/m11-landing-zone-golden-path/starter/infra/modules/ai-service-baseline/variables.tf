# --- Identity of the service: these values become the mandatory tags ---

variable "service_name" {
  description = "Service name, in kebab-case: assistant-rh. Prefix of every resource name."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.service_name))
    error_message = "Invalid service_name: kebab-case, 3 to 31 characters."
  }
}

variable "team" {
  description = "Owning team, carried by the Team tag (ABAC)."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*$", var.team))
    error_message = "team must be a lowercase identifier, for example rh."
  }
}

variable "cost_center" {
  description = "Cost center, carried by the CostCenter tag."
  type        = string

  validation {
    condition     = length(trimspace(var.cost_center)) > 0
    error_message = "cost_center is required."
  }
}

variable "data_classification" {
  description = "Classification of the data the service handles, carried by the DataClassification tag."
  type        = string

  validation {
    condition     = contains(["public", "interne", "confidentiel"], var.data_classification)
    error_message = "data_classification must be public, interne or confidentiel."
  }
}

variable "tags" {
  description = "Additional tags. The four mandatory tags always take precedence."
  type        = map(string)
  default     = {}
}

# --- Budget ---

variable "monthly_budget_usd" {
  description = "Monthly budget of the account, in dollars."
  type        = number

  validation {
    condition     = var.monthly_budget_usd > 0
    error_message = "monthly_budget_usd must be greater than 0."
  }
}

variable "budget_email" {
  description = "Address that receives the budget alerts."
  type        = string

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.budget_email))
    error_message = "budget_email must be an email address."
  }
}

# --- Runtime ---

variable "trusted_services" {
  description = "Service principals allowed to assume the execution role (Lambda by default)."
  type        = list(string)
  default     = ["lambda.amazonaws.com"]

  validation {
    condition     = length(var.trusted_services) > 0 && alltrue([for s in var.trusted_services : endswith(s, ".amazonaws.com")])
    error_message = "trusted_services must list AWS service principals, such as lambda.amazonaws.com."
  }
}

variable "bedrock_resource_arns" {
  description = "ARNs of the allowed Bedrock models or inference profiles (module M12). Empty: no Bedrock access."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for arn in var.bedrock_resource_arns : startswith(arn, "arn:") && !strcontains(arn, "*")])
    error_message = "bedrock_resource_arns must be explicit ARNs, without wildcards."
  }
}

# --- Guardrails: each default is the compliant choice, and only compliant values pass ---

variable "sse_algorithm" {
  description = "Server-side encryption of the bucket: aws:kms or aws:kms:dsse, always with the service key."
  type        = string
  default     = "aws:kms"

  validation {
    condition     = contains(["aws:kms", "aws:kms:dsse"], var.sse_algorithm)
    error_message = "Socle IA: every S3 bucket must be encrypted with a KMS key (aws:kms or aws:kms:dsse)."
  }
}

variable "log_retention_days" {
  description = "Retention of the log group, in days. Bounded: logs are never kept forever."
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365], var.log_retention_days)
    error_message = "log_retention_days must be one of 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180 or 365."
  }
}

variable "kms_deletion_window_days" {
  description = "Waiting period before the key is deleted, in days (7 to 30)."
  type        = number
  default     = 7

  validation {
    condition     = var.kms_deletion_window_days >= 7 && var.kms_deletion_window_days <= 30
    error_message = "kms_deletion_window_days must be between 7 and 30."
  }
}

variable "ephemeral" {
  description = "true in a lab: terraform destroy deletes everything, data included. false keeps the log group and refuses to delete a bucket that still holds objects."
  type        = bool
  default     = false
}
