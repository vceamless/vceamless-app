terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Raw web data bucket for SF Ventures scrape
resource "aws_s3_bucket" "raw_web" {
  bucket = "vceamless-raw-web-031561760771"

  tags = {
    Project = "vceamless"
    Env     = "dev"
    Purpose = "raw-web-ingestion"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "raw_web" {
  bucket = aws_s3_bucket.raw_web.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

# Enable default AES256 encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "raw_web" {
  bucket = aws_s3_bucket.raw_web.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
