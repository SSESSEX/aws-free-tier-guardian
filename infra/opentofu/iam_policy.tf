data "aws_iam_policy_document" "guardian_read_only" {
  statement {
    sid    = "AllowCallerIdentityCheck"
    effect = "Allow"

    actions = [
      "sts:GetCallerIdentity"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "AllowS3ReadOnlyInventory"
    effect = "Allow"

    actions = [
      "s3:ListAllMyBuckets",
      "s3:GetBucketLocation",
      "s3:GetBucketAcl",
      "s3:GetBucketPolicy",
      "s3:GetBucketPolicyStatus",
      "s3:GetBucketPublicAccessBlock",
      "s3:GetEncryptionConfiguration",
      "s3:GetBucketVersioning",
      "s3:GetBucketOwnershipControls",
      "s3:GetBucketTagging"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "AllowEC2ReadOnlyInventory"
    effect = "Allow"

    actions = [
      "ec2:DescribeInstances",
      "ec2:DescribeVolumes",
      "ec2:DescribeAddresses",
      "ec2:DescribeSecurityGroups",
      "ec2:DescribeNetworkInterfaces",
      "ec2:DescribeRegions",
      "ec2:DescribeTags"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "AllowCloudWatchLogsReadOnlyInventory"
    effect = "Allow"

    actions = [
      "logs:DescribeLogGroups",
      "logs:ListTagsForResource",
      "logs:ListTagsLogGroup"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "AllowIAMAccessKeyReadOnlyInventory"
    effect = "Allow"

    actions = [
      "iam:ListUsers",
      "iam:ListAccessKeys",
      "iam:GetAccessKeyLastUsed",
      "iam:ListUserTags"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "AllowCloudTrailReadOnlyInventory"
    effect = "Allow"

    actions = [
      "cloudtrail:DescribeTrails",
      "cloudtrail:GetTrailStatus",
      "cloudtrail:ListTags"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "AllowRDSReadOnlyInventory"
    effect = "Allow"

    actions = [
      "rds:DescribeDBInstances",
      "rds:ListTagsForResource"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_policy" "guardian_read_only" {
  name        = var.guardian_read_only_policy_name
  description = "Least-privilege read-only policy for AWS Free-Tier Guardian scanner."
  policy      = data.aws_iam_policy_document.guardian_read_only.json
}