terraform {
  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.73.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Course    = "intelligence-training"
      Lab       = "m13-agentcore-support-agent"
      Stack     = "support-agent"
      ManagedBy = "terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id    = data.aws_caller_identity.current.account_id
  project_dir   = "${path.module}/../../SupportLab"
  agentcore_arn = "arn:aws:bedrock-agentcore:${var.region}:${local.account_id}"

  # Lower-case names: Gateway and Runtime IDs are derived from them.
  runtime_name           = "${var.project_name}_agent"
  memory_name            = "${var.project_name}_agentMemory"
  gateway_name           = "${replace(var.project_name, "_", "-")}-tools"
  credential_name        = "${replace(var.project_name, "_", "-")}-acme"
  policy_engine_name     = "${var.project_name}_guard"
  online_eval_name       = "${var.project_name}_SupportMonitor"
  workload_directory_arn = "${local.agentcore_arn}:workload-identity-directory/default"
}

# Trust policy shared by the roles that AgentCore assumes (runtime, gateway, evaluation).
data "aws_iam_policy_document" "agentcore_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["${local.agentcore_arn}:*"]
    }
  }
}
