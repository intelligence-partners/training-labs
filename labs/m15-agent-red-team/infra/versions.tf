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
      lab = "m15-agent-red-team"
    }
  }
}
