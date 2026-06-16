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
