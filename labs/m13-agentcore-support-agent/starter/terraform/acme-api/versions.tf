terraform {
  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.73.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "2.8.1"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Course    = "intelligence-training"
      Lab       = "m13-agentcore-support-agent"
      Stack     = "acme-api"
      ManagedBy = "terraform"
    }
  }
}
