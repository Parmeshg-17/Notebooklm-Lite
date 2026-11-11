# ── Random suffix for globally unique S3 bucket naming ──
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# ── 1. Document Storage Bucket (Private Documents & Research Papers) ──
resource "aws_s3_bucket" "documents" {
  bucket        = "${var.project_name}-documents-${var.environment}-${random_string.bucket_suffix.result}"
  force_destroy = false

  tags = {
    Name    = "${var.project_name}-documents-${var.environment}"
    Purpose = "Document Storage"
  }
}

# Block all public access
resource "aws_s3_bucket_public_access_block" "documents_public_block" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Server-Side Encryption (AES256)
resource "aws_s3_bucket_server_side_encryption_configuration" "documents_crypto" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Versioning for document auditability
resource "aws_s3_bucket_versioning" "documents_versioning" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Lifecycle Rule to transition older versions
resource "aws_s3_bucket_lifecycle_configuration" "documents_lifecycle" {
  bucket = aws_s3_bucket.documents.id

  rule {
    id     = "archive-old-versions"
    status = "Enabled"

    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}

# ── 2. Frontend Static Assets Bucket (Private, accessed strictly via CloudFront OAC) ──
resource "aws_s3_bucket" "frontend" {
  bucket        = "${var.project_name}-frontend-${var.environment}-${random_string.bucket_suffix.result}"
  force_destroy = true

  tags = {
    Name    = "${var.project_name}-frontend-${var.environment}"
    Purpose = "Frontend Static Web Hosting"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend_public_block" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "frontend_crypto" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket Policy granting access strictly to CloudFront OAC
resource "aws_s3_bucket_policy" "frontend_oac_policy" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipalReadOnly"
        Effect    = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.cdn.arn
          }
        }
      }
    ]
  })
}

