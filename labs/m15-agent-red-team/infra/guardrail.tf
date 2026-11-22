# Step 8: D4 with Amazon Bedrock Guardrails. garde.ticket_bloque() calls ApplyGuardrail on the
# ticket with this guardrail (BEDROCK_GUARDRAIL_ID) and its working draft (version DRAFT).

resource "aws_bedrock_guardrail" "prompt_attack" {
  name        = "m15-redteam-prompt-attack"
  description = "M15 lab: prompt attack filter applied to tickets before the agent reads them."

  blocked_input_messaging   = "Ticket bloqué par le filtre d'attaques de prompt."
  blocked_outputs_messaging = "Réponse bloquée par le guardrail."

  content_policy_config {
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = var.prompt_attack_strength
      output_strength = "NONE" # the prompt attack filter applies to inputs only
    }
  }
}
