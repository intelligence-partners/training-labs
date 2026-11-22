# Step 2 (part 1): the vector store. The console "quick create" builds the same pieces:
# an OpenSearch Serverless collection, its encryption, network and data access policies,
# and a k-NN vector index.

locals {
  collection_name = var.lab_name
  index_name      = "bedrock-knowledge-base-default-index"

  # Field names used by the console quick create, mapped in the Knowledge Base below.
  vector_field   = "bedrock-knowledge-base-default-vector"
  text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
  metadata_field = "AMAZON_BEDROCK_METADATA"

  # The faiss engine is required for metadata filtering (step 4 filters on "service").
  index_body = {
    settings = {
      index = {
        knn                        = true
        "knn.algo_param.ef_search" = 512
      }
    }
    mappings = {
      properties = {
        (local.vector_field) = {
          type      = "knn_vector"
          dimension = var.embedding_dimensions
          method = {
            name       = "hnsw"
            engine     = "faiss"
            space_type = "l2"
            parameters = { ef_construction = 512, m = 16 }
          }
        }
        (local.text_field)     = { type = "text", index = true }
        (local.metadata_field) = { type = "text", index = false }
      }
    }
  }
}

resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${var.lab_name}-enc"
  type = "encryption"
  policy = jsonencode({
    Rules       = [{ ResourceType = "collection", Resource = ["collection/${local.collection_name}"] }]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "network" {
  name = "${var.lab_name}-net"
  type = "network"
  # Reachable endpoint, like the console quick create; every call still needs SigV4 and the data access policy.
  policy = jsonencode([{
    Rules           = [{ ResourceType = "collection", Resource = ["collection/${local.collection_name}"] }]
    AllowFromPublic = true
  }])
}

resource "aws_opensearchserverless_access_policy" "data" {
  name = "${var.lab_name}-data"
  type = "data"
  policy = jsonencode([
    {
      Description = "Knowledge Base: read and write the vectors"
      Principal   = [aws_iam_role.knowledge_base.arn]
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/${local.collection_name}"]
          Permission   = ["aoss:DescribeCollectionItems"]
        },
        {
          ResourceType = "index"
          Resource     = ["index/${local.collection_name}/*"]
          Permission   = ["aoss:DescribeIndex", "aoss:ReadDocument", "aoss:WriteDocument", "aoss:UpdateIndex"]
        },
      ]
    },
    {
      Description = "Index builder function: create the vector index once"
      Principal   = [aws_iam_role.index_builder.arn]
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/${local.collection_name}"]
          Permission   = ["aoss:DescribeCollectionItems"]
        },
        {
          ResourceType = "index"
          Resource     = ["index/${local.collection_name}/*"]
          Permission   = ["aoss:CreateIndex", "aoss:DescribeIndex"]
        },
      ]
    },
  ])
}

resource "aws_opensearchserverless_collection" "kb" {
  name = local.collection_name
  type = "VECTORSEARCH"
  # Default redundancy, as in the cost section of the lesson (billed per OCU-hour while it exists).
  standby_replicas = "ENABLED"

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
  ]
}

# --- Vector index -------------------------------------------------------------------------
# Neither hashicorp/aws nor awscc creates a k-NN index (awscc_opensearchserverless_collection_index
# wraps the CreateIndex API, which builds automatic semantic enrichment indexes). A small function
# signs the OpenSearch REST call with its role, and Terraform invokes it once.

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "index_builder" {
  name               = "${var.lab_name}-index"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

resource "aws_cloudwatch_log_group" "index_builder" {
  name              = "/aws/lambda/${var.lab_name}-index"
  retention_in_days = var.log_retention_days
}

data "aws_iam_policy_document" "index_builder" {
  statement {
    sid       = "OpenSearchServerlessApi"
    actions   = ["aoss:APIAccessAll"]
    resources = [aws_opensearchserverless_collection.kb.arn]
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.index_builder.arn}:*"]
  }
}

resource "aws_iam_role_policy" "index_builder" {
  name   = "create-vector-index"
  role   = aws_iam_role.index_builder.id
  policy = data.aws_iam_policy_document.index_builder.json
}

data "archive_file" "index_builder" {
  type        = "zip"
  source_file = "${path.module}/../index_builder/index_builder.py"
  output_path = "${path.module}/build/index_builder.zip"
}

resource "aws_lambda_function" "index_builder" {
  function_name    = "${var.lab_name}-index"
  role             = aws_iam_role.index_builder.arn
  runtime          = "python3.12"
  handler          = "index_builder.handler"
  filename         = data.archive_file.index_builder.output_path
  source_code_hash = data.archive_file.index_builder.output_base64sha256
  timeout          = 300
  memory_size      = 256

  depends_on = [aws_cloudwatch_log_group.index_builder, aws_iam_role_policy.index_builder]
}

resource "aws_lambda_invocation" "vector_index" {
  function_name = aws_lambda_function.index_builder.function_name
  input = jsonencode({
    endpoint = aws_opensearchserverless_collection.kb.collection_endpoint
    index    = local.index_name
    body     = local.index_body
  })

  # The data access policy must exist before the function calls the collection.
  depends_on = [aws_opensearchserverless_access_policy.data]
}
