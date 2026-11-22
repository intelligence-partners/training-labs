terraform {
  required_version = ">= 1.5.7"

  required_providers {
    # A reusable module states the range it supports; each root module pins
    # the exact version (and its .terraform.lock.hcl records the checksums).
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.72.0, < 7.0.0"
    }
  }
}
