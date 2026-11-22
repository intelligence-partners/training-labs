# Step 5: the guardrail (Classic tier) and its version 1.

resource "aws_bedrock_guardrail" "this" {
  name                      = var.lab_name
  description               = "Guardrail du lab assistant RH"
  blocked_input_messaging   = "Je ne peux pas traiter cette demande. Pour une situation personnelle, contactez directement le service RH."
  blocked_outputs_messaging = "Je ne trouve pas de réponse fiable dans les documents disponibles. Contactez le service RH."

  # TODO (step 5): content_policy_config with six filters_config blocks: HATE, INSULTS, SEXUAL,
  # VIOLENCE and MISCONDUCT at HIGH on input and output, PROMPT_ATTACK at HIGH on input and
  # NONE on output.

  # TODO (step 5): topic_policy_config that DENYs the topic "Conseil juridique individuel"
  # (definition and two examples: see the lesson).

  # TODO (step 5): sensitive_information_policy_config: ANONYMIZE EMAIL and PHONE in outputs
  # only (input_enabled = false), BLOCK INTERNATIONAL_BANK_ACCOUNT_NUMBER.

  # TODO (step 5): contextual_grounding_policy_config with GROUNDING and RELEVANCE at 0.5.
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
