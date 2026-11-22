output "bucket" {
  description = "Bucket that holds the documents (BUCKET in the lesson)."
  value       = aws_s3_bucket.docs.id
}

output "kb_id" {
  description = "Knowledge Base ID (KB_ID)."
  value       = aws_bedrockagent_knowledge_base.this.id
}

output "ds_id" {
  description = "Data source ID (DS_ID)."
  value       = aws_bedrockagent_data_source.docs.data_source_id
}

output "collection_arn" {
  description = "OpenSearch Serverless collection ARN (COLL_ARN)."
  value       = aws_opensearchserverless_collection.kb.arn
}

output "guardrail_id" {
  description = "Guardrail ID (GR_ID)."
  value       = aws_bedrock_guardrail.this.guardrail_id
}

output "guardrail_version" {
  description = "Guardrail version (GR_VERSION)."
  value       = aws_bedrock_guardrail_version.v1.version
}

output "profile_arn" {
  description = "Inference profile ARN (PROFILE_ARN)."
  value       = local.profile_arn
}

output "function_name" {
  description = "Lambda function name."
  value       = aws_lambda_function.rag.function_name
}

output "api_id" {
  description = "HTTP API ID (API_ID)."
  value       = aws_apigatewayv2_api.rag.id
}

output "api_url" {
  description = "HTTP API endpoint (API_URL)."
  value       = aws_apigatewayv2_api.rag.api_endpoint
}
