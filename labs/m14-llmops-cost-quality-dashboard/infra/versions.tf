terraform {
  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 6.72.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      lab = "m14-llmops-cost-quality-dashboard"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  namespace  = "M14/AgentSupport"
}
