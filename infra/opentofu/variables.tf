variable "aws_profile" {
  description = "Local AWS CLI profile used by OpenTofu."
  type        = string
  default     = "guardian-dev"
}

variable "aws_region" {
  description = "AWS region for regional resources."
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "dev"
}

variable "guardian_read_only_policy_name" {
  description = "Name of the IAM policy used by AWS Free-Tier Guardian scanner."
  type        = string
  default     = "aws-free-tier-guardian-read-only"
}