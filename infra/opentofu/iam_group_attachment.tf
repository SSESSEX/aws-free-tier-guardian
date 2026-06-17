data "aws_iam_group" "guardian_scanner_group" {
  group_name = var.guardian_scanner_group_name
}

resource "aws_iam_group_policy_attachment" "guardian_read_only_to_scanner_group" {
  group      = data.aws_iam_group.guardian_scanner_group.group_name
  policy_arn = aws_iam_policy.guardian_read_only.arn
}