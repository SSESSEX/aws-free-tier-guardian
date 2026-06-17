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

output "guardian_read_only_policy_name" {
  description = "Name of the AWS Free-Tier Guardian read-only IAM policy."
  value       = aws_iam_policy.guardian_read_only.name
}

output "guardian_read_only_policy_arn_redacted" {
  description = "Redacted IAM policy ARN placeholder."
  value       = "POLICY_ARN_REDACTED"
}