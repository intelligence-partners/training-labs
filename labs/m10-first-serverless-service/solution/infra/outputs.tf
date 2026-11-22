output "api_url" {
  description = "Base URL of the API"
  value       = aws_apigatewayv2_api.prompts.api_endpoint
}

output "table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.prompts.name
}

output "function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.prompts.function_name
}
