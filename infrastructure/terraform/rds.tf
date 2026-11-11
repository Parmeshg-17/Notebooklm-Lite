# ── 1. Secure Random Password for Master User ──
resource "random_password" "db_password" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# ── 2. AWS Secrets Manager Secret for Database Credentials ──
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${var.project_name}-db-credentials-${var.environment}"
  description             = "Master database credentials and DATABASE_URL for NotebookLM Lite"
  recovery_window_in_days = 0

  tags = {
    Name = "${var.project_name}-db-secret-${var.environment}"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials_val" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    engine   = "postgres"
    host     = aws_db_instance.postgres.address
    port     = aws_db_instance.postgres.port
    username = var.db_username
    password = random_password.db_password.result
    database = var.db_name
    database_url = "postgresql+asyncpg://${var.db_username}:${random_password.db_password.result}@${aws_db_instance.postgres.address}:${aws_db_instance.postgres.port}/${var.db_name}"
  })
}

# ── 3. DB Subnet Group across Private Subnets ──
resource "aws_db_subnet_group" "rds" {
  name        = "${var.project_name}-db-subnet-group-${var.environment}"
  description = "Subnet group for RDS PostgreSQL across private subnets"
  subnet_ids  = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group-${var.environment}"
  }
}

# ── 4. DB Parameter Group for PostgreSQL 16 ──
resource "aws_db_parameter_group" "pg16" {
  name   = "${var.project_name}-pg16-params-${var.environment}"
  family = "postgres16"

  # Performance and connection settings
  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  tags = {
    Name = "${var.project_name}-pg16-params-${var.environment}"
  }
}

# ── 5. Amazon RDS PostgreSQL Database Instance ──
resource "aws_db_instance" "postgres" {
  identifier             = "${var.project_name}-db-${var.environment}"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage
  max_allocated_storage  = 100 # Auto-minor storage scaling up to 100GB
  storage_type           = "gp3"
  storage_encrypted      = true # AWS KMS encryption at rest

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.rds.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.pg16.name

  publicly_accessible = false # Enforce zero public exposure
  multi_az            = var.environment == "production" ? true : false

  backup_retention_period   = 7
  backup_window             = "03:00-04:00"
  maintenance_window        = "Mon:04:00-Mon:05:00"
  auto_minor_version_upgrade = true
  deletion_protection       = var.environment == "production" ? true : false
  skip_final_snapshot       = var.environment == "production" ? false : true
  final_snapshot_identifier = "${var.project_name}-final-snapshot-${var.environment}"

  tags = {
    Name = "${var.project_name}-rds-postgres-${var.environment}"
  }
}

