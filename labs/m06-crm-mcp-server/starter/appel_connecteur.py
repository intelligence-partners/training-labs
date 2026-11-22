# Step 7: call the server from the Messages API with the MCP connector.
# The API connects to the server itself, from Anthropic's infrastructure: the server must be
# reachable on a public HTTPS URL (CRM_PUBLIC_URL, e.g. a cloudflared quick tunnel).
import os

import anthropic

client = anthropic.Anthropic()
url = os.environ["CRM_PUBLIC_URL"].rstrip("/") + "/mcp"

# TODO(step 7): call client.beta.messages.create with
# - model="claude-opus-5-5", max_tokens=16000, betas=["mcp-client-2025-11-20"]
# - mcp_servers=[{"type": "url", "url": url, "name": "orbis", "authorization_token": os.environ["CRM_TOKEN"]}]
# - tools=[{"type": "mcp_toolset", "mcp_server_name": "orbis",
#           "configs": {"crm_add_note": {"enabled": False}}}]   # deny list: read-only assistant
# - one user message: "Quels clients et prospects avons-nous à Lyon ? Donne leur statut."
response = None

# TODO(step 7): print each block of response.content:
# - mcp_tool_use  -> f"[appel] {block.server_name}.{block.name} {block.input}"
# - mcp_tool_result -> f"[résultat] erreur={block.is_error}"
# - text -> block.text
# then print("stop_reason :", response.stop_reason)
raise SystemExit(f"TODO(step 7): call {url} through the MCP connector")
