"""Optional provider switch (not in the lesson): the step 7 question through Amazon Bedrock.

MCP is an open standard: the same orbis-crm server works with any host that speaks MCP
(Claude Code, the Messages API connector, other agent platforms and SDKs). The MCP
connector of appel_connecteur.py is a Claude API feature; Bedrock's Converse API has no
connector, so this script is the MCP client itself:

1. it starts server.py over stdio (no tunnel, no token: everything stays local);
2. it lists the server's tools and hands them to the model as Converse tools,
   minus crm_add_note (the same deny list as the connector: read-only assistant);
3. it runs each tool call on the MCP server and sends the result back, until the
   model answers.

Run (no tunnel, no CRM_TOKEN, no Anthropic key needed):
    BEDROCK_MODEL_ID=<a model enabled in your account that supports tool use> python bedrock_mcp_client.py
or, with the same switch as the other labs:
    MODEL_PROVIDER=bedrock BEDROCK_MODEL_ID=... python appel_connecteur.py
"""

import os
import sys
from pathlib import Path

import anyio

from mcp import Client, StdioServerParameters

QUESTION = "Quels clients et prospects avons-nous à Lyon ? Donne leur statut."
SERVER_NAME = "orbis"
DISABLED_TOOLS = {"crm_add_note"}  # deny list: no writes from this assistant
MAX_TURNS = 10
MAX_TOKENS = 16000


def to_converse_tool(tool) -> dict:
    """An MCP tool definition as a Converse toolSpec (same name, description and JSON schema)."""
    return {
        "toolSpec": {
            "name": tool.name,
            "description": tool.description or tool.name,
            "inputSchema": {"json": tool.input_schema},
        }
    }


def result_text(result) -> str:
    return "\n".join(block.text for block in result.content if getattr(block, "type", None) == "text")


async def ask(question: str, mcp_client, bedrock, model_id: str, out=print) -> str | None:
    """Run the tool loop. Returns the final stop reason."""
    listed = await mcp_client.list_tools()
    tools = [to_converse_tool(t) for t in listed.tools if t.name not in DISABLED_TOOLS]
    messages = [{"role": "user", "content": [{"text": question}]}]

    stop_reason = None
    for _ in range(MAX_TURNS):
        response = bedrock.converse(
            modelId=model_id,
            messages=messages,
            toolConfig={"tools": tools},
            inferenceConfig={"maxTokens": MAX_TOKENS},
        )
        stop_reason = response["stopReason"]
        message = response["output"]["message"]
        messages.append(message)

        results = []
        for block in message["content"]:
            if "text" in block:
                out(block["text"])
            elif "toolUse" in block:
                use = block["toolUse"]
                out(f"[appel] {SERVER_NAME}.{use['name']} {use['input']}")
                if use["name"] in DISABLED_TOOLS:  # never offered, refuse it anyway
                    text, is_error = f"L'outil {use['name']} est désactivé pour cet assistant.", True
                else:
                    result = await mcp_client.call_tool(use["name"], use["input"])
                    text, is_error = result_text(result), bool(result.is_error)
                out(f"[résultat] erreur={is_error}")
                results.append({
                    "toolResult": {
                        "toolUseId": use["toolUseId"],
                        "content": [{"text": text or "(vide)"}],
                        "status": "error" if is_error else "success",
                    }
                })
        if stop_reason != "tool_use":
            break
        messages.append({"role": "user", "content": results})

    out(f"stop_reason : {stop_reason}")
    return stop_reason


def server_parameters() -> StdioServerParameters:
    env = {k: os.environ[k] for k in ("CRM_DATA",) if k in os.environ}
    return StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).resolve().parent / "server.py")],
        env=env or None,
    )


def main() -> int:
    model_id = os.environ.get("BEDROCK_MODEL_ID", "").strip()
    if not model_id:
        print("Définissez BEDROCK_MODEL_ID avec l'identifiant d'un modèle activé dans votre compte.", file=sys.stderr)
        return 2

    import boto3

    bedrock = boto3.client("bedrock-runtime")

    async def run() -> None:
        async with Client(server_parameters()) as mcp_client:
            await ask(QUESTION, mcp_client, bedrock, model_id)

    anyio.run(run)
    return 0


if __name__ == "__main__":
    sys.exit(main())

