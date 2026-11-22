# Step 2 (part 2): the Knowledge Base, its service role and its S3 data source.
# Parsing and chunking stay at their defaults, as in the lesson.

locals {
  embedding_model_arn = "arn:aws:bedrock:${var.region}::foundation-model/${var.embedding_model_id}"
}

data "aws_iam_policy_document" "knowledge_base_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:bedrock:${var.region}:${local.account_id}:knowledge-base/*"]
    }
  }
}

resource "aws_iam_role" "knowledge_base" {
  name               = "${var.lab_name}-kb"
  assume_role_policy = data.aws_iam_policy_document.knowledge_base_trust.json
}

data "aws_iam_policy_document" "knowledge_base" {
  statement {
    sid       = "Embeddings"
    actions   = ["bedrock:InvokeModel"]
    resources = [local.embedding_model_arn]
  }
  statement {
    sid       = "VectorStore"
    actions   = ["aoss:APIAccessAll"]
    resources = [aws_opensearchserverless_collection.kb.arn]
  }
  statement {
    sid       = "ListDocuments"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.docs.arn]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [local.account_id]
    }
  }
  statement {
    sid       = "ReadDocuments"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.docs.arn}/docs/*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [local.account_id]
    }
  }
}

resource "aws_iam_role_policy" "knowledge_base" {
  name   = "knowledge-base"
  role   = aws_iam_role.knowledge_base.id
  policy = data.aws_iam_policy_document.knowledge_base.json
}

resource "aws_bedrockagent_knowledge_base" "this" {
  name     = var.knowledge_base_name
  role_arn = aws_iam_role.knowledge_base.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = local.embedding_model_arn
      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = var.embedding_dimensions
          embedding_data_type = "FLOAT32"
        }
      }
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.kb.arn
      vector_index_name = local.index_name
      field_mapping {
        vector_field   = local.vector_field
        text_field     = local.text_field
        metadata_field = local.metadata_field
      }
    }
  }

  depends_on = [
    aws_lambda_invocation.vector_index,
    aws_iam_role_policy.knowledge_base,
  ]
}

resource "aws_bedrockagent_data_source" "docs" {
  name              = "${var.lab_name}-docs"
  knowledge_base_id = aws_bedrockagent_knowledge_base.this.id

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn         = aws_s3_bucket.docs.arn
      inclusion_prefixes = ["docs/"]
    }
  }

  depends_on = [aws_s3_object.docs]
}
