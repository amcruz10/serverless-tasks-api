variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short name used to prefix resources"
  type        = string
  default     = "tasks-api"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "log_retention_days" {
  description = "CloudWatch log retention for the Lambda function"
  type        = number
  default     = 14
}
