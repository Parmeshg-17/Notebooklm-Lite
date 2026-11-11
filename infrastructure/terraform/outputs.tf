output "vpc_id" {
  value       = aws_vpc.main.id
  description = "VPC ID"
}

output "public_subnet_ids" {
  value       = aws_subnet.public[*].id
  description = "Public subnet IDs"
}

output "private_subnet_ids" {
  value       = aws_subnet.private[*].id
  description = "Private subnet IDs"
}

output "alb_dns_name" {
  value       = aws_lb.main.dns_name
  description = "DNS name of the public Application Load Balancer"
}

output "alb_target_group_arn" {
  value       = aws_lb_target_group.backend.arn
  description = "Target group ARN for backend ECS tasks"
}

output "cloudfront_domain_name" {
  value       = aws_cloudfront_distribution.cdn.domain_name
  description = "CloudFront CDN domain URL for the frontend application"
}

output "cloudfront_distribution_id" {
  value       = aws_cloudfront_distribution.cdn.id
  description = "CloudFront Distribution ID for cache invalidations"
}

output "s3_documents_bucket_name" {
  value       = aws_s3_bucket.documents.id
  description = "Private S3 bucket name for document PDF storage"
}

output "s3_frontend_bucket_name" {
  value       = aws_s3_bucket.frontend.id
  description = "Private S3 bucket name for React SPA build assets"
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.backend.repository_url
  description = "Amazon ECR repository URL for backend container images"
}

output "rds_endpoint" {
  value       = aws_db_instance.postgres.address
  description = "Amazon RDS PostgreSQL connection host (private)"
}

output "rds_port" {
  value       = aws_db_instance.postgres.port
  description = "Amazon RDS PostgreSQL connection port"
}

output "secrets_manager_db_arn" {
  value       = aws_secretsmanager_secret.db_credentials.arn
  description = "Secrets Manager ARN for database credentials"
}

output "secrets_manager_app_arn" {
  value       = aws_secretsmanager_secret.app_secrets.arn
  description = "Secrets Manager ARN for application API keys"
}

output "github_oidc_role_arn" {
  value       = aws_iam_role.github_oidc.arn
  description = "IAM Role ARN for GitHub Actions OIDC authentication"
}

