output "api_endpoint" {
  description = "Base URL for the deployed API"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

output "dynamodb_table_name" {
  value = aws_dynamodb_table.tasks.name
}

output "lambda_function_name" {
  value = aws_lambda_function.tasks_api.function_name
}
