# ── 1. Application Load Balancer Security Group ──
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg-${var.environment}"
  description = "Security group for public facing Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  # Inbound HTTP (port 80)
  ingress {
    description = "Allow inbound HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Inbound HTTPS (port 443)
  ingress {
    description = "Allow inbound HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound traffic (ALB forwards traffic to target group targets in private subnets)
  egress {
    description = "Allow outbound traffic from ALB to targets"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg-${var.environment}"
  }
}

# ── 2. Amazon ECS Fargate Task Security Group ──
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-task-sg-${var.environment}"
  description = "Security group for ECS Fargate backend application tasks"
  vpc_id      = aws_vpc.main.id

  # Ingress strictly from ALB on container port 8000
  ingress {
    description     = "Allow traffic strictly from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Outbound egress for API calls, package fetches, and database connections
  egress {
    description = "Allow all outbound traffic from ECS tasks"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-task-sg-${var.environment}"
  }
}

# ── 3. Amazon RDS PostgreSQL Security Group ──
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg-${var.environment}"
  description = "Security group strictly isolating Amazon RDS PostgreSQL in private subnets"
  vpc_id      = aws_vpc.main.id

  # Ingress strictly from ECS Task Security Group
  ingress {
    description     = "Allow PostgreSQL access strictly from ECS backend tasks"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  # No outbound egress required for database
  egress {
    description = "Disallow outbound egress from database"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg-${var.environment}"
  }
}

