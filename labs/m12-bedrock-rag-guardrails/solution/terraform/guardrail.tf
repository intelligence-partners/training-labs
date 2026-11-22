# Step 5: the guardrail (Classic tier) and its version 1.
# E-mails and phone numbers are masked in outputs only (input_enabled = false), so that an
# employee who gives their own contact details is not blocked.

locals {
  content_filters = {
    HATE          = { input = "HIGH", output = "HIGH" }
    INSULTS       = { input = "HIGH", output = "HIGH" }
    SEXUAL        = { input = "HIGH", output = "HIGH" }
    VIOLENCE      = { input = "HIGH", output = "HIGH" }
    MISCONDUCT    = { input = "HIGH", output = "HIGH" }
    PROMPT_ATTACK = { input = "HIGH", output = "NONE" }
  }
}

resource "aws_bedrock_guardrail" "this" {
  name                      = var.lab_name
  description               = "Guardrail du lab assistant RH"
  blocked_input_messaging   = "Je ne peux pas traiter cette demande. Pour une situation personnelle, contactez directement le service RH."
  blocked_outputs_messaging = "Je ne trouve pas de réponse fiable dans les documents disponibles. Contactez le service RH."

  content_policy_config {
    dynamic "filters_config" {
      for_each = local.content_filters
      content {
        type            = filters_config.key
        input_strength  = filters_config.value.input
        output_strength = filters_config.value.output
      }
    }
  }

  topic_policy_config {
    topics_config {
      name       = "Conseil juridique individuel"
      definition = "Demande d'avis juridique sur la situation personnelle d'un salarié, par exemple un litige, un licenciement ou une rupture conventionnelle."
      examples = [
        "Mon manager veut me licencier, que dois-je faire juridiquement ?",
        "Puis-je attaquer mon employeur aux prud'hommes ?",
      ]
      type = "DENY"
    }
  }

  sensitive_information_policy_config {
    pii_entities_config {
      type          = "EMAIL"
      action        = "ANONYMIZE"
      input_enabled = false
    }
    pii_entities_config {
      type          = "PHONE"
      action        = "ANONYMIZE"
      input_enabled = false
    }
    pii_entities_config {
      type   = "INTERNATIONAL_BANK_ACCOUNT_NUMBER"
      action = "BLOCK"
    }
  }

  # 0.5 is a cautious starting point for the Classic tier, which judges grounding strictly.
  contextual_grounding_policy_config {
    filters_config {
      type      = "GROUNDING"
      threshold = 0.5
    }
    filters_config {
      type      = "RELEVANCE"
      threshold = 0.5
    }
  }
}

# A version is an immutable snapshot: cut a new one whenever the guardrail changes, so that the
# function (GUARDRAIL_VERSION) always uses the current policies.
resource "aws_bedrock_guardrail_version" "v1" {
  guardrail_arn = aws_bedrock_guardrail.this.guardrail_arn
  description   = "Version 1 du lab"

  lifecycle {
    replace_triggered_by = [aws_bedrock_guardrail.this]
  }
}
