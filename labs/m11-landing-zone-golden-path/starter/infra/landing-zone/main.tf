# Simplified landing zone of Socle IA: six OUs and four SCPs.

# --- Organizational units ---

resource "aws_organizations_organizational_unit" "top" {
  for_each = toset(["Security", "Infrastructure", "Sandbox", "Workloads"])

  name      = each.key
  parent_id = var.root_id
}

# TODO (step 4): an aws_organizations_organizational_unit "workloads" that creates
#   the Dev and Prod OUs (for_each), with parent_id set to the id of
#   aws_organizations_organizational_unit.top["Workloads"].

# --- Service control policies ---

locals {
  # Global services whose endpoint is in us-east-1: do not block them.
  global_services = [
    "account:*", "budgets:*", "ce:*", "cloudfront:*", "health:*", "iam:*",
    "organizations:*", "route53:*", "sso:*", "sts:*", "support:*",
  ]

  # Principals exempt from the protection SCPs, in every account. With Identity
  # Center, the PlatformAdmin permission set role too (its suffix changes when
  # the permission set is recreated, hence the wildcards).
  platform_principals = concat(
    ["arn:aws:iam::*:role/${var.platform_role_name}"],
    var.enable_identity_center ? ["arn:aws:iam::*:role/aws-reserved/sso.amazonaws.com/*/AWSReservedSSO_PlatformAdmin_*"] : [],
  )

  # Attachment targets, by name: the root and the OUs.
  targets = merge(
    { Root = var.root_id },
    { for name, ou in aws_organizations_organizational_unit.top : name => ou.id },
  )

  scps = {
    DenyLeaveOrganization = {
      description = "Prevents leaving the organization or closing an account"
      # On the root: every current and future member account. SCPs never
      # affect the management account.
      targets = ["Root"]
      statement = {
        Sid      = "DenyLeaveOrganizationAndCloseAccount"
        Effect   = "Deny"
        Action   = ["organizations:LeaveOrganization", "account:CloseAccount"]
        Resource = "*"
      }
    }

    # TODO (step 4): DenyOutsideAllowedRegions, "Restricts member accounts to the
    #   allowed Regions", on Security, Infrastructure, Sandbox and Workloads (not
    #   the root): Deny with NotAction = local.global_services, Resource "*", and
    #   the conditions StringNotEquals aws:RequestedRegion = var.allowed_regions
    #   and ArnNotLike aws:PrincipalArn = local.platform_principals.

    # TODO (step 4): ProtectSecurityBaseline, "Prevents disabling logging and
    #   detection", on Infrastructure, Sandbox and Workloads (not Security): Deny
    #   cloudtrail:DeleteTrail, cloudtrail:StopLogging, cloudtrail:UpdateTrail,
    #   config:DeleteConfigurationRecorder, config:DeleteDeliveryChannel,
    #   config:StopConfigurationRecorder, guardduty:DeleteDetector,
    #   guardduty:DisassociateFromAdministratorAccount,
    #   securityhub:DisableSecurityHub and access-analyzer:DeleteAnalyzer, except
    #   for local.platform_principals (ArnNotLike on aws:PrincipalArn).

    # TODO (step 4): DenyIamUsers, "No IAM users and no long-term access keys",
    #   on Sandbox and Workloads: Deny iam:CreateUser, iam:CreateAccessKey and
    #   iam:CreateLoginProfile (Sid DenyIamUsersAndAccessKeys).
  }

  # One attachment per (SCP, target) pair, keyed by names known at plan time.
  attachments = merge([
    for scp, def in local.scps : { for target in def.targets : "${scp}/${target}" => { scp = scp, target = target } }
  ]...)
}

resource "aws_organizations_policy" "scp" {
  for_each = local.scps

  name        = each.key
  description = each.value.description
  type        = "SERVICE_CONTROL_POLICY"
  content = jsonencode({
    Version   = "2012-10-17"
    Statement = [each.value.statement]
  })
}

resource "aws_organizations_policy_attachment" "scp" {
  for_each = local.attachments

  policy_id = aws_organizations_policy.scp[each.value.scp].id
  target_id = local.targets[each.value.target]
}
