variable "region" {
  description = "AWS Region of the lab."
  type        = string
  default     = "eu-west-3"
}

variable "acme_api_key" {
  description = "Key of the existing API, checked in the x-api-key header. Pass it with TF_VAR_acme_api_key; never commit it."
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.acme_api_key) >= 32
    error_message = "Use a long random key, for example: openssl rand -hex 24."
  }
}

variable "log_retention_days" {
  description = "Retention of the function's log group."
  type        = number
  default     = 7
}
