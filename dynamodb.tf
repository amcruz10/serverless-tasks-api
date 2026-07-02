resource "aws_dynamodb_table" "tasks" {
  name         = "${var.project_name}-${var.environment}"
  billing_mode = "PAY_PER_REQUEST" # no capacity planning needed, scales to zero
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  # Encryption at rest, on by default with AWS-owned key.
  # For a real workload you'd point this at a customer-managed KMS key
  # so you control rotation and access policy independently of AWS.
  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = true
  }
}
