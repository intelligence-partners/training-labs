# Step 4 (part 1): the key of the existing API goes into the Identity token vault. The agent never
# sees it: the Gateway reads it and injects it in the x-api-key header (gateway.tf).
# The key is also in the Terraform state (local and git-ignored here). In production, reference a
# Secrets Manager secret with api_key_secret_config, or use api_key_wo with Terraform >= 1.11.

resource "aws_bedrockagentcore_api_key_credential_provider" "acme" {
  name    = local.credential_name
  api_key = var.acme_api_key
}
