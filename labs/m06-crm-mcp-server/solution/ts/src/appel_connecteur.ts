import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();
const url = `${process.env.CRM_PUBLIC_URL!.replace(/\/$/, "")}/mcp`;

const response = await client.beta.messages.create({
  model: "claude-opus-5-5",
  max_tokens: 16000,
  betas: ["mcp-client-2025-11-20"],
  mcp_servers: [{ type: "url", url, name: "orbis", authorization_token: process.env.CRM_TOKEN }],
  tools: [{ type: "mcp_toolset", mcp_server_name: "orbis", configs: { crm_add_note: { enabled: false } } }],
  messages: [{ role: "user", content: "Quels clients et prospects avons-nous à Lyon ? Donne leur statut." }],
});

for (const block of response.content) {
  if (block.type === "mcp_tool_use") console.log(`[appel] ${block.server_name}.${block.name}`, block.input);
  else if (block.type === "mcp_tool_result") console.log(`[résultat] erreur=${block.is_error}`);
  else if (block.type === "text") console.log(block.text);
}
