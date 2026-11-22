variable "root_id" {
  description = "ID of the organization root, r-xxxx (export TF_VAR_root_id)."
  type        = string

  validation {
    condition     = can(regex("^r-[0-9a-z]{4,32}$", var.root_id))
    error_message = "root_id must look like r-ab12: run aws organizations list-roots."
  }
}

variable "allowed_regions" {
  description = "Regions allowed for member accounts."
  type        = list(string)
  default     = ["eu-west-3", "eu-west-1"]

  validation {
    condition     = length(var.allowed_regions) > 0
    error_message = "Allow at least one Region."
  }
}

variable "platform_role_name" {
  description = "Platform role, exempt from the protection SCPs, in every account."
  type        = string
  default     = "SoclePlatformAdmin"
}

variable "enable_identity_center" {
  description = "true creates the permission sets of the Socle IA catalog. Requires IAM Identity Center enabled for the organization."
  type        = bool
  default     = false
}
