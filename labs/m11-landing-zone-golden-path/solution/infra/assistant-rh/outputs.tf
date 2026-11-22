output "bucket_name" {
  description = "Name of the data bucket"
  value       = module.assistant_rh.bucket_name
}

output "kms_key_id" {
  description = "ID of the service KMS key"
  value       = module.assistant_rh.kms_key_id
}

output "log_group_name" {
  description = "Name of the encrypted log group"
  value       = module.assistant_rh.log_group_name
}

output "role_arn" {
  description = "ARN of the execution role"
  value       = module.assistant_rh.role_arn
}

output "budget_name" {
  description = "Name of the monthly budget"
  value       = module.assistant_rh.budget_name
}
