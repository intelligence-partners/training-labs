output "table_name" {
  description = "Name of the DynamoDB table"
  value       = aws_dynamodb_table.prompts.name
}

# TODO (step 2): an output "api_url" (description "Base URL of the API") with
#   the api_endpoint of the HTTP API, and an output "function_name".
