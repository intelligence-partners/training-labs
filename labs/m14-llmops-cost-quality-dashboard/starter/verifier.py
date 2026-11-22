"""M14 lab, step 2: check that you can invoke Claude Opus 5.5 in Bedrock from eu-west-3."""
from anthropic import AnthropicBedrock

client = AnthropicBedrock(aws_region="eu-west-3")
r = client.messages.create(
    model="eu.anthropic.claude-opus-5-5",
    max_tokens=1024,
    output_config={"effort": "low"},
    messages=[{"role": "user", "content": "Réponds seulement par le mot : prêt"}],
)
print(r.stop_reason, [b.text for b in r.content if b.type == "text"], r.usage.input_tokens, r.usage.output_tokens)
