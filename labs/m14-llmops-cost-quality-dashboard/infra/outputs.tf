output "account_id" {
  value = local.account_id
}

output "sns_topic_arn" {
  description = "ARN of the alert topic."
  value       = aws_sns_topic.alertes.arn
}

output "dashboard_name" {
  value = aws_cloudwatch_dashboard.agent_support.dashboard_name
}

output "invocation_log_group" {
  value = aws_cloudwatch_log_group.bedrock_invocations.name
}

output "alarm_names" {
  value = [
    aws_cloudwatch_metric_alarm.cout_moyen_tache.alarm_name,
    aws_cloudwatch_metric_alarm.taux_reussite.alarm_name,
    aws_cloudwatch_metric_alarm.taux_cache.alarm_name,
  ]
}

output "transaction_search_managed_by_lab" {
  description = "true when this lab enabled Transaction Search (cleanup.sh then disables it)."
  value       = var.enable_transaction_search
}

output "region" {
  value = var.region
}
