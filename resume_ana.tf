# Terraform configuration for Resume Analyzer infrastructure

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region to deploy the infrastructure"
  default     = "us-east-1"
}

variable "app_name" {
  description = "Application name"
  default     = "resume-analyzer"
}

variable "environment" {
  description = "Deployment environment"
  default     = "dev"
}

# S3 bucket for storing resumes
resource "aws_s3_bucket" "resume_bucket" {
  bucket = "${var.app_name}-${var.environment}-resumes"
  
  tags = {
    Name        = "${var.app_name}-${var.environment}-resumes"
    Environment = var.environment
  }
}

# S3 bucket policy
resource "aws_s3_bucket_policy" "resume_bucket_policy" {
  bucket = aws_s3_bucket.resume_bucket.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action    = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource  = [
          "${aws_s3_bucket.resume_bucket.arn}/*"
        ]
      }
    ]
  })
}

# OpenSearch Domain
resource "aws_opensearch_domain" "resume_analysis" {
  domain_name    = "${var.app_name}-${var.environment}"
  engine_version = "OpenSearch_2.5"
  
  cluster_config {
    instance_type = "t3.small.search"
    instance_count = 1
  }
  
  ebs_options {
    ebs_enabled = true
    volume_size = 10
  }
  
  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = {
          AWS = "*"
        }
        Action    = "es:*"
        Resource  = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${var.app_name}-${var.environment}/*"
      }
    ]
  })
  
  tags = {
    Name        = "${var.app_name}-${var.environment}-opensearch"
    Environment = var.environment
  }
}

# RDS Aurora Serverless PostgreSQL
resource "aws_rds_cluster" "analysis_db" {
  cluster_identifier   = "${var.app_name}-${var.environment}"
  engine               = "aurora-postgresql"
  engine_mode          = "serverless"
  database_name        = "resume_analysis"
  master_username      = "admin"
  master_password      = random_password.db_password.result
  skip_final_snapshot  = true
  
  scaling_configuration {
    auto_pause               = true
    min_capacity             = 2
    max_capacity             = 8
    seconds_until_auto_pause = 300
  }
  
  tags = {
    Name        = "${var.app_name}-${var.environment}-db"
    Environment = var.environment
  }
}

# Generate random password for RDS
resource "random_password" "db_password" {
  length  = 16
  special = false
}

# Store database credentials in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name = "${var.app_name}-${var.environment}-db-credentials"
  
  tags = {
    Name        = "${var.app_name}-${var.environment}-db-credentials"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id     = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = aws_rds_cluster.analysis_db.master_username
    password = aws_rds_cluster.analysis_db.master_password
    engine   = "postgres"
    host     = aws_rds_cluster.analysis_db.endpoint
    port     = aws_rds_cluster.analysis_db.port
    dbname   = aws_rds_cluster.analysis_db.database_name
  })
}

# Lambda function for resume analysis
resource "aws_lambda_function" "resume_analyzer" {
  function_name = "${var.app_name}-${var.environment}-analyzer"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  timeout       = 300
  memory_size   = 1024
  
  filename      = "lambda_function.zip"
  
  environment {
    variables = {
      RESUME_BUCKET      = aws_s3_bucket.resume_bucket.bucket
      OPENSEARCH_DOMAIN  = aws_opensearch_domain.resume_analysis.endpoint
      RDS_SECRET_ARN     = aws_secretsmanager_secret.db_credentials.arn
      RDS_CLUSTER_ARN    = aws_rds_cluster.analysis_db.arn
      DATABASE_NAME      = aws_rds_cluster.analysis_db.database_name
    }
  }
  
  tags = {
    Name        = "${var.app_name}-${var.environment}-analyzer"
    Environment = var.environment
  }
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.app_name}-${var.environment}-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action    = "sts:AssumeRole"
      }
    ]
  })
  
  tags = {
    Name        = "${var.app_name}-${var.environment}-lambda-role"
    Environment = var.environment
  }
}

# IAM policy for Lambda
resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.app_name}-${var.environment}-lambda-policy"
  description = "Policy for resume analyzer Lambda function"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "comprehend:DetectKeyPhrases",
          "comprehend:DetectEntities",
          "textract:DetectDocumentText",
          "textract:AnalyzeDocument",
          "es:ESHttpGet",
          "es:ESHttpPost",
          "es:ESHttpPut",
          "es:ESHttpDelete",
          "rds-data:ExecuteStatement",
          "secretsmanager:GetSecretValue"
        ],
        Resource = "*"
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "lambda_policy_attachment" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# API Gateway for Resume Analyzer
resource "aws_api_gateway_rest_api" "resume_analyzer_api" {
  name        = "${var.app_name}-${var.environment}-api"
  description = "API Gateway for Resume Analyzer"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
  
  tags = {
    Name        = "${var.app_name}-${var.environment}-api"
    Environment = var.environment
  }
}

# API Gateway resource for /analyze endpoint
resource "aws_api_gateway_resource" "analyze_resource" {
  rest_api_id = aws_api_gateway_rest_api.resume_analyzer_api.id
  parent_id   = aws_api_gateway_rest_api.resume_analyzer_api.root_resource_id
  path_part   = "analyze"
}

# API Gateway resource for /reports endpoint
resource "aws_api_gateway_resource" "reports_resource" {
  rest_api_id = aws_api_gateway_rest_api.resume_analyzer_api.id
  parent_id   = aws_api_gateway_rest_api.resume_analyzer_api.root_resource_id
  path_part   = "reports"
}

# API Gateway resource for /reports/{reportId} endpoint
resource "aws_api_gateway_resource" "report_resource" {
  rest_api_id = aws_api_gateway_rest_api.resume_analyzer_api.id
  parent_id   = aws_api_gateway_resource.reports_resource.id
  path_part   = "{reportId}"
}

# API Gateway method for POST /analyze
resource "aws_api_gateway_method" "analyze_post" {
  rest_api_id   = aws_api_gateway_rest_api.resume_analyzer_api.id
  resource_id   = aws_api_gateway_resource.analyze_resource.id
  http_method   = "POST"
  authorization_type = "NONE"
}

# API Gateway method for GET /reports
resource "aws_api_gateway_method" "reports_get" {
  rest_api_id   = aws_api_gateway_rest_api.resume_analyzer_api.id
  resource_id   = aws_api_gateway_resource.reports_resource.id
  http_method   = "GET"
  authorization_type = "NONE"
}

# API Gateway method for GET /reports/{reportId}
resource "aws_api_gateway_method" "report_get" {
  rest_api_id   = aws_api_gateway_rest_api.resume_analyzer_api.id
  resource_id   = aws_api_gateway_resource.report_resource.id
  http_method   = "GET"
  authorization_type = "NONE"
}

# API Gateway integration for POST /analyze
resource "aws_api_gateway_integration" "analyze_integration" {
  rest_api_id             = aws_api_gateway_rest_api.resume_analyzer_api.id
  resource_id             = aws_api_gateway_resource.analyze_resource.id
  http_method             = aws_api_gateway_method.analyze_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.resume_analyzer.invoke_arn
}

# API Gateway integration for GET /reports
resource "aws_api_gateway_integration" "reports_integration" {
  rest_api_id             = aws_api_gateway_rest_api.resume_analyzer_api.id
  resource_id             = aws_api_gateway_resource.reports_resource.id
  http_method             = aws_api_gateway_method.reports_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.resume_analyzer.invoke_arn
}

# API Gateway integration for GET /reports/{reportId}
resource "aws_api_gateway_integration" "report_integration" {
  rest_api_id             = aws_api_gateway_rest_api.resume_analyzer_api.id
  resource_id             = aws_api_gateway_resource.report_resource.id
  http_method             = aws_api_gateway_method.report_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.resume_analyzer.invoke_arn
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.resume_analyzer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.resume_analyzer_api.execution_arn}/*/*"
}

# API Gateway deployment
resource "aws_api_gateway_deployment" "api_deployment" {
  depends_on = [
    aws_api_gateway_integration.analyze_integration,
    aws_api_gateway_integration.reports_integration,
    aws_api_gateway_integration.report_integration
  ]
  
  rest_api_id = aws_api_gateway_rest_api.resume_analyzer_api.id
  stage_name  = var.environment
}

# Create RDS DB initialization Lambda
resource "aws_lambda_function" "db_init" {
  function_name = "${var.app_name}-${var.environment}-db-init"
  role          = aws_iam_role.lambda_role.arn
  handler       = "db_init.lambda_handler"
  runtime       = "python3.9"
  timeout       = 30
  memory_size   = 128
  
  filename      = "db_init.zip"
  
  environment {
    variables = {
      RDS_SECRET_ARN  = aws_secretsmanager_secret.db_credentials.arn
      RDS_CLUSTER_ARN = aws_rds_cluster.analysis_db.arn
      DATABASE_NAME   = aws_rds_cluster.analysis_db.database_name
    }
  }
  
  tags = {
    Name        = "${var.app_name}-${var.environment}-db-init"
    Environment = var.environment
  }
}

# Data source for current AWS account ID
data "aws_caller_identity" "current" {}

# Outputs
output "api_endpoint" {
  value = aws_api_gateway_deployment.api_deployment.invoke_url
}

output "opensearch_endpoint" {
  value = aws_opensearch_domain.resume_analysis.endpoint
}

output "rds_endpoint" {
  value = aws_rds_cluster.analysis_db.endpoint
}

output "s3_bucket" {
  value = aws_s3_bucket.resume_bucket.bucket
}