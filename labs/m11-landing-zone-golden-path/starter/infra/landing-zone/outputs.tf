output "workloads_ou_id" {
  description = "ID of the Workloads OU"
  value       = aws_organizations_organizational_unit.top["Workloads"].id
}

# TODO (step 4): outputs "dev_ou_id" and "prod_ou_id", with the ids of the Dev
#   and Prod OUs.

output "scp_ids" {
  description = "IDs of the SCPs, by name"
  value       = { for name, policy in aws_organizations_policy.scp : name => policy.id }
}

output "permission_set_arns" {
  description = "ARNs of the permission sets (empty unless enable_identity_center is true)"
  value       = { for name, set in aws_ssoadmin_permission_set.this : name => set.arn }
}
