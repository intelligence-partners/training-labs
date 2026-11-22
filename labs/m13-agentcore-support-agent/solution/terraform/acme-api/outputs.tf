output "api_id" {
  description = "HTTP API ID (API_ID in the lesson)."
  value       = aws_apigatewayv2_api.acme_api.id
}

output "api_url" {
  description = "HTTP API endpoint (API_URL in the lesson), the server URL of the OpenAPI schema."
  value       = aws_apigatewayv2_api.acme_api.api_endpoint
}

output "function_name" {
  description = "Function of the existing API."
  value       = aws_lambda_function.acme_api.function_name
}
