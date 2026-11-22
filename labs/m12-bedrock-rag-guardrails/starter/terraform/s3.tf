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

# TODO (step 1): an aws_s3_object "docs" with for_each = local.docs_files that uploads each
# file of ../docs under the "docs/" prefix (key "docs/${each.value}"), with
# etag = filemd5(...) so that a modified document is uploaded again. Expected: six objects.
# Then add aws_s3_object.docs to the depends_on of the data source in knowledge_base.tf.
