terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Production remote state backend configuration with S3 and DynamoDB locking.
  # Run `terraform init -backend-config="bucket=..."` to configure dynamically.
  # backend "s3" {
  #   bucket         = "notebooklm-terraform-state-ap-south-1"
  #   key            = "production/terraform.tfstate"
  #   region         = "ap-south-1"
  #   dynamodb_table = "notebooklm-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "NotebookLM-Lite"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "PlatformEngineering"
    }
  }
}

