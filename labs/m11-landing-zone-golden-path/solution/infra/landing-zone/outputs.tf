output "workloads_ou_id" {
  description = "ID of the Workloads OU"
  value       = aws_organizations_organizational_unit.top["Workloads"].id
}

output "dev_ou_id" {
  description = "ID of the Dev OU, under Workloads"
  value       = aws_organizations_organizational_unit.workloads["Dev"].id
}

output "prod_ou_id" {
  description = "ID of the Prod OU, under Workloads"
  value       = aws_organizations_organizational_unit.workloads["Prod"].id
}

output "scp_ids" {
  description = "IDs of the four SCPs, by name"
  value       = { for name, policy in aws_organizations_policy.scp : name => policy.id }
}

output "permission_set_arns" {
  description = "ARNs of the permission sets (empty unless enable_identity_center is true)"
  value       = { for name, set in aws_ssoadmin_permission_set.this : name => set.arn }
}
