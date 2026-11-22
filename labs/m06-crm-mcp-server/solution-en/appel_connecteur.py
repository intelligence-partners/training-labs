# Step 7: call the server from the Messages API with the MCP connector.
# The API connects to the server itself, from Anthropic's infrastructure: the server must be
# reachable on a public HTTPS URL (CRM_PUBLIC_URL, e.g. a cloudflared quick tunnel).
# The write tool is disabled in the toolset: the assistant called from the API is read-only.
import os

import anthropic

if os.environ.get("MODEL_PROVIDER", "anthropic") == "bedrock":
    # Optional provider switch (not in the lesson): Bedrock has no MCP connector, so
    # bedrock_mcp_client.py acts as the MCP client itself, over stdio. See that file.
    from bedrock_mcp_client import main

    raise SystemExit(main())

client = anthropic.Anthropic()
url = os.environ["CRM_PUBLIC_URL"].rstrip("/") + "/mcp"

response = client.beta.messages.create(
    model="claude-opus-5-5",
    max_tokens=16000,
    betas=["mcp-client-2025-11-20"],
    mcp_servers=[{"type": "url", "url": url, "name": "orbis", "authorization_token": os.environ["CRM_TOKEN"]}],
    tools=[
        {
            "type": "mcp_toolset",
            "mcp_server_name": "orbis",
            "configs": {"crm_add_note": {"enabled": False}},  # denylist: no writes
        }
    ],
    messages=[{"role": "user", "content": "Which customers and prospects do we have in Lyon? Give their status."}],
)

for block in response.content:
    if block.type == "mcp_tool_use":
        print(f"[call] {block.server_name}.{block.name} {block.input}")
    elif block.type == "mcp_tool_result":
        print(f"[result] error={block.is_error}")
    elif block.type == "text":
        print(block.text)
print("stop_reason:", response.stop_reason)
