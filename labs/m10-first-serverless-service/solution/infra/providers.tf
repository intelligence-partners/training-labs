terraform {
  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.72.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "2.8.1"
    }
  }
}

provider "aws" {
  region = var.region

  # Cost allocation tags, set on every resource that supports tags.
  default_tags {
    tags = var.tags
  }
}
