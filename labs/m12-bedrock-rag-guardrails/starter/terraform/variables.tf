variable "region" {
  description = "AWS Region of the lab. The lesson runs in Paris."
  type        = string
  default     = "eu-west-3"
}

variable "model_id" {
  description = "Inference profile ID used by the Converse API. Any profile whose model family is enabled in the account works (list them with: aws bedrock list-inference-profiles)."
  type        = string
  default     = "eu.anthropic.claude-opus-5-5"
}

variable "model_effort" {
  description = "Anthropic effort level passed through additionalModelRequestFields. Set it to an empty string for a model family that does not accept output_config."
  type        = string
  default     = "low"
}

variable "embedding_model_id" {
  description = "Embedding model of the Knowledge Base."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "embedding_dimensions" {
  description = "Vector size produced by the embedding model (Titan Text Embeddings V2: 1024)."
  type        = number
  default     = 1024
}

variable "lab_name" {
  description = "Name shared by the bucket prefix, the collection, the guardrail, the function and the API."
  type        = string
  default     = "lab-rag-rh"
}

variable "knowledge_base_name" {
  description = "Name of the Knowledge Base."
  type        = string
  default     = "kb-lab-rh"
}

variable "log_retention_days" {
  description = "Retention of the CloudWatch log groups created by the lab."
  type        = number
  default     = 7
}
