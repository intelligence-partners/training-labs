output "bucket_name" {
  description = "Name of the data bucket"
  value       = aws_s3_bucket.data.bucket
}

output "bucket_arn" {
  description = "ARN of the data bucket"
  value       = aws_s3_bucket.data.arn
}

output "kms_key_id" {
  description = "ID of the service KMS key"
  value       = aws_kms_key.this.key_id
}

output "kms_key_arn" {
  description = "ARN of the service KMS key"
  value       = aws_kms_key.this.arn
}

output "kms_alias" {
  description = "Alias of the service KMS key"
  value       = aws_kms_alias.this.name
}

output "log_group_name" {
  description = "Name of the encrypted log group"
  value       = aws_cloudwatch_log_group.this.name
}

output "role_arn" {
  description = "ARN of the execution role"
  value       = aws_iam_role.runtime.arn
}

output "role_name" {
  description = "Name of the execution role"
  value       = aws_iam_role.runtime.name
}

output "budget_name" {
  description = "Name of the monthly budget"
  value       = aws_budgets_budget.monthly.name
}
