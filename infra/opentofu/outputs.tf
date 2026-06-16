output "aws_account_id_redacted" {
  description = "Redacted AWS account identifier."
  value       = "ACCOUNT_ID_REDACTED"
}

output "aws_region" {
  description = "Current AWS region."
  value       = data.aws_region.current.region
}

output "project" {
  description = "Project name."
  value       = "AWSFreeTierGuardian"
}

output "environment" {
  description = "Environment name."
  value       = var.environment
}