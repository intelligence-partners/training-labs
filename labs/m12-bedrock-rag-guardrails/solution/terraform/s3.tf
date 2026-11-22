# Step 1: the bucket and the three internal documents, each with its metadata file.

locals {
  account_id = data.aws_caller_identity.current.account_id
  bucket     = "${var.lab_name}-${local.account_id}"
  docs_dir   = "${path.module}/../docs"
  docs_files = fileset(local.docs_dir, "*")
}

resource "aws_s3_bucket" "docs" {
  bucket = local.bucket
  # The lab bucket only holds fictitious documents: destroy empties it.
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "docs" {
  bucket                  = aws_s3_bucket.docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "docs" {
  for_each = local.docs_files

  bucket       = aws_s3_bucket.docs.id
  key          = "docs/${each.value}"
  source       = "${local.docs_dir}/${each.value}"
  etag         = filemd5("${local.docs_dir}/${each.value}")
  content_type = endswith(each.value, ".json") ? "application/json" : "text/markdown; charset=utf-8"
}
