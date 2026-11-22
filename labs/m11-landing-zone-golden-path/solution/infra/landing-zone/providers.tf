terraform {
  required_version = ">= 1.5.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.72.0"
    }
  }
}

# Organizations is a global service: its resources have no Region.
provider "aws" {
  region = "eu-west-3"

  default_tags {
    tags = {
      Projet        = "formation-m11"
      Environnement = "lab"
    }
  }
}
