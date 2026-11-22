# The memory of the agent-python-strands template (AgentCore CLI 1.0.1): short-term events and
# four long-term strategies. USER_PREFERENCE fills /users/{actorId}/preferences (step 8).

resource "aws_bedrockagentcore_memory" "agent_memory" {
  name                  = local.memory_name
  event_expiry_duration = var.memory_event_expiry_days
}

# Strategies are added one after the other: each one updates the same memory.
resource "aws_bedrockagentcore_memory_strategy" "semantic" {
  name                = "Semantic"
  memory_id           = aws_bedrockagentcore_memory.agent_memory.id
  type                = "SEMANTIC"
  namespace_templates = ["/users/{actorId}/facts"]
}

resource "aws_bedrockagentcore_memory_strategy" "user_preference" {
  name                = "UserPreference"
  memory_id           = aws_bedrockagentcore_memory.agent_memory.id
  type                = "USER_PREFERENCE"
  namespace_templates = ["/users/{actorId}/preferences"]

  depends_on = [aws_bedrockagentcore_memory_strategy.semantic]
}

resource "aws_bedrockagentcore_memory_strategy" "summarization" {
  name                = "Summarization"
  memory_id           = aws_bedrockagentcore_memory.agent_memory.id
  type                = "SUMMARIZATION"
  namespace_templates = ["/summaries/{actorId}/{sessionId}"]

  depends_on = [aws_bedrockagentcore_memory_strategy.user_preference]
}

resource "aws_bedrockagentcore_memory_strategy" "episodic" {
  name                = "Episodic"
  memory_id           = aws_bedrockagentcore_memory.agent_memory.id
  type                = "EPISODIC"
  namespace_templates = ["/episodes/{actorId}/{sessionId}"]

  reflection_configuration {
    namespace_templates = ["/episodes/{actorId}"]
  }

  depends_on = [aws_bedrockagentcore_memory_strategy.summarization]
}
