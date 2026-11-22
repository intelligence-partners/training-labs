# Optional: the permission sets of the Socle IA catalog (Identity Center lesson).
# Off by default. Turn it on with TF_VAR_enable_identity_center=true once IAM
# Identity Center is enabled for the organization (from the console: it cannot
# be enabled through the API). Group assignments are left out: the groups come
# from your identity provider. The Developer permission set is left out too: it
# references the customer managed policy socle-developer, which must first exist
# in every target account.

data "aws_ssoadmin_instances" "this" {
  count = var.enable_identity_center ? 1 : 0
}

locals {
  sso_instance_arn = var.enable_identity_center ? tolist(data.aws_ssoadmin_instances.this[0].arns)[0] : null

  permission_sets = {
    PlatformAdmin = {
      description = "Platform team, every account except management"
      policies    = ["arn:aws:iam::aws:policy/AdministratorAccess"]
    }
    SecurityAudit = {
      description = "Security team, every account"
      policies    = ["arn:aws:iam::aws:policy/SecurityAudit", "arn:aws:iam::aws:policy/job-function/ViewOnlyAccess"]
    }
    ProdReadOnly = {
      description = "Product teams, their Prod accounts"
      policies    = ["arn:aws:iam::aws:policy/job-function/ViewOnlyAccess", "arn:aws:iam::aws:policy/CloudWatchLogsReadOnlyAccess"]
    }
    BillingViewer = {
      description = "Financial control, management account"
      policies    = ["arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess"]
    }
  }

  permission_set_policies = merge([
    for name, set in local.permission_sets : { for arn in set.policies : "${name}/${arn}" => { set = name, arn = arn } }
  ]...)
}

resource "aws_ssoadmin_permission_set" "this" {
  for_each = var.enable_identity_center ? local.permission_sets : {}

  name             = each.key
  description      = each.value.description
  instance_arn     = local.sso_instance_arn
  session_duration = "PT1H"
}

resource "aws_ssoadmin_managed_policy_attachment" "this" {
  for_each = var.enable_identity_center ? local.permission_set_policies : {}

  instance_arn       = local.sso_instance_arn
  permission_set_arn = aws_ssoadmin_permission_set.this[each.value.set].arn
  managed_policy_arn = each.value.arn
}
