variable "region" {
  description = "AWS Region of the lab (the lesson uses eu-west-3, Paris)."
  type        = string
  default     = "eu-west-3"
}

variable "alert_email" {
  description = "Email address that receives the alarm notifications (step 9) and the budget alerts (step 10)."
  type        = string
}

variable "enable_transaction_search" {
  description = <<-EOT
    Step 4. Run `aws xray get-trace-segment-destination` first. If the destination is already
    CloudWatchLogs with the ACTIVE status, set false: the lab then leaves Transaction Search as it is.
    Set true to let the lab enable it (and cleanup.sh disable it).
  EOT
  type        = bool
}

variable "model_id_observe" {
  description = <<-EOT
    Step 8. Value of the ModelId dimension under which Bedrock publishes your calls, from
    `aws cloudwatch list-metrics --namespace AWS/Bedrock --metric-name Invocations`.
    Update it and apply again after the first run if it differs from the default.
  EOT
  type        = string
  default     = "eu.anthropic.claude-opus-5-5"
}

variable "cost_alarm_threshold" {
  description = "Step 9. Average cost per task (USD) that triggers m14-cout-moyen-tache: twice the v1 average cost noted at step 6."
  type        = number
  default     = 0.08
}

variable "budget_limit_usd" {
  description = "Step 10. Monthly budget of the lab account, in USD."
  type        = string
  default     = "10"
}
