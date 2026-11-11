variable "aws_region" {
  type        = string
  description = "Target AWS Region"
  default     = "ap-south-1"
}

variable "environment" {
  type        = string
  description = "Deployment environment name (dev, staging, production)"
  default     = "production"
}

variable "project_name" {
  type        = string
  description = "Project name prefix for AWS resources"
  default     = "notebooklm"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the custom VPC"
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  type        = list(string)
  description = "CIDR blocks for public subnets (ALB & NAT)"
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  type        = list(string)
  description = "CIDR blocks for private subnets (ECS & RDS)"
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "db_name" {
  type        = string
  description = "PostgreSQL database name"
  default     = "notebooklm"
}

variable "db_username" {
  type        = string
  description = "RDS master username"
  default     = "notebooklm_admin"
}

variable "db_instance_class" {
  type        = string
  description = "RDS PostgreSQL compute tier (db.t4g.micro for Free Tier / dev; db.t4g.small/medium for prod)"
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type        = number
  description = "RDS allocated storage in GB"
  default     = 20
}

variable "ecs_cpu" {
  type        = number
  description = "Fargate vCPU units (256 = 0.25 vCPU, 512 = 0.5 vCPU, 1024 = 1 vCPU)"
  default     = 512
}

variable "ecs_memory" {
  type        = number
  description = "Fargate memory allocation in MB (1024 = 1GB, 2048 = 2GB)"
  default     = 1024
}

variable "backend_desired_count" {
  type        = number
  description = "Desired number of running ECS backend tasks"
  default     = 2
}

variable "backend_min_count" {
  type        = number
  description = "Minimum number of tasks for Autoscaling"
  default     = 1
}

variable "backend_max_count" {
  type        = number
  description = "Maximum number of tasks for Autoscaling"
  default     = 4
}

variable "google_api_key" {
  type        = string
  description = "Google Gemini API key (stored in Secrets Manager)"
  sensitive   = true
  default     = ""
}

variable "qdrant_url" {
  type        = string
  description = "Qdrant Cloud cluster URL"
  default     = "https://85ac0602-f166-4f07-9957-b138b4272250.us-west-1-0.aws.cloud.qdrant.io:6333"
}

variable "qdrant_api_key" {
  type        = string
  description = "Qdrant API key"
  sensitive   = true
  default     = ""
}

variable "github_repo" {
  type        = string
  description = "GitHub repository identifier in format 'org/repo' for OIDC trust"
  default     = "org/notebooklm-lite"
}

