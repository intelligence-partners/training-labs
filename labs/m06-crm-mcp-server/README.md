# Lab m06: an MCP server for your CRM

Companion code for the lab that closes module **M06, Tool use and the Model Context Protocol**, of the Intelligence Training course (lesson "Lab: an MCP server for your CRM"). French version: [README.fr.md](README.fr.md).

## Goal

Build **orbis-crm**, the MCP server of a fictitious CRM, and serve it to three different clients: MCP Inspector, Claude Code, and the Messages API through the MCP connector. The server exposes two tools (`crm_search_clients`, `crm_add_note`), a parameterized resource (`crm://clients/{client_id}`) and a prompt (`preparer_rendez_vous`).

The Model Context Protocol is an open standard: the same server works with any MCP host, not only Anthropic's. In this lab it is used by MCP Inspector, Claude Code and the Claude API connector; the optional `bedrock_mcp_client.py` shows a fourth host, a small MCP client of your own that lets a model on Amazon Bedrock call the same tools, and the tests drive both the Python and the TypeScript servers with one generic MCP client.

## Architecture

| Element | Role |
| --- | --- |
| `crm_data.json` | Six fictitious customers, with their notes |
| `server.py` | The MCP server (MCP Python SDK v2, `MCPServer`): stdio by default, Streamable HTTP with `--http`, protected by a static token read from `CRM_TOKEN` |
| MCP Inspector | Test client, over stdio then over HTTP |
| Claude Code | Local host, over stdio |
| cloudflared tunnel | Exposes the local server on a temporary public HTTPS URL |
| `appel_connecteur.py` | The Messages API connects to the server itself (MCP connector), with the write tool disabled |
| `ts/` | The TypeScript variant of the server (MCP TypeScript SDK v2: stdio entry point and Express HTTP entry point) and of the connector call |

The server reads and writes `crm_data.json` (path computed from the file, or `CRM_DATA`). Over HTTP, a request without the token gets `401` with a `WWW-Authenticate` header that points to the protected resource metadata (RFC 9728) published by the SDK; the public tunnel host is added to the allowed hosts, otherwise the DNS rebinding protection answers `421`. Responses are plain JSON (`json_response=True`) because quick tunnels do not support SSE.

## Two editions of the code

Tool, resource and prompt names, function names and data keys are the same as in both editions of the lesson. Descriptions, messages and the fictitious data follow the language of the lesson you are reading:

| Folder | Lesson | Descriptions, messages, data |
| --- | --- | --- |
| `starter-en/`, `solution-en/` | English lesson (`content-en`) | English (`[call] orbis.crm_search_clients ...`) |
| `starter/`, `solution/` | French lesson | French (`[appel] orbis.crm_search_clients ...`) |

```text
m06-crm-mcp-server/
├── README.md, README.fr.md
├── .env.example              variables the lab reads (CRM_TOKEN, CRM_PUBLIC_URL, ...)
├── requirements.txt          mcp[cli], anthropic (step 1)
├── requirements-bedrock.txt  + boto3, for the optional Bedrock client
├── requirements-dev.txt      + pytest, for the tests
├── test.sh                   offline checks (also run by CI)
├── cleanup.sh                removes the Claude Code registrations of the lab
├── starter-en/ starter/      server.py and appel_connecteur.py with TODO(step N) markers, ts/ with TODOs
├── solution-en/ solution/
│   ├── crm_data.json server.py appel_connecteur.py
│   ├── bedrock_mcp_client.py optional: Bedrock Converse + your own MCP client (not in the lesson)
│   └── ts/                   src/crm.ts, src/stdio.ts, src/http.ts, src/appel_connecteur.ts
└── tests/                    offline tests
```

## Prerequisites

From the lesson:

- Python 3.11 or later;
- Node.js 22.19 or later, for MCP Inspector (the current Inspector release, 2.16.0, declares Node `^22.23.4 || ^24.22.1 || >=26.12.1`);
- Claude Code installed and signed in, or another local MCP host by adapting step 4;
- an Anthropic API key in `ANTHROPIC_API_KEY`, for step 7 (model access: `claude-opus-5-5`, MCP connector beta `mcp-client-2025-11-20`);
- `cloudflared` for step 7 (`brew install cloudflared` on macOS, or your system's package); no Cloudflare account is needed for a quick tunnel.

Optional Bedrock client: an AWS account with access to a Bedrock model that supports tool use, and AWS credentials on your machine.

Tested with Python 3.12, Node.js 20 (servers and type check; the Inspector itself needs Node 22), `mcp` 2.3.0, `anthropic` 2.12.0, `@modelcontextprotocol/server` 2.4.0, `@modelcontextprotocol/express` 2.0.2, `@modelcontextprotocol/node` 2.1.2, `express` 5.3.0, `zod` 4.6.7, `@anthropic-ai/sdk` 1.12.0, `boto3` 1.44.9.

## Estimated cost

As stated in the lesson: steps 1 to 6 cost nothing beyond your usual Claude Code usage. Step 7 sends a few requests to `claude-opus-5-5`: with tool definitions and results, count a few thousand input tokens and a few hundred output tokens per request, a few cents each. **The whole lab stays under one dollar.** No cloud resource is created.

The tests in this repository cost nothing: they never call a model.

## Run it

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m06-crm-mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd starter-en          # complete the TODOs; or cd solution-en to run the finished server
```

The lesson's commands use `$(pwd)/.venv/bin/python`. In this repository the virtual environment is one level up, so use `$(pwd)/../.venv/bin/python`, or simply `"$(which python)"` with the environment activated:

| Lesson step | Where | Command |
| --- | --- | --- |
| 1. Set up the project | the commands above | `crm_data.json` is already there |
| 2. Write the server | `server.py`, `TODO(step 2)` | `python server.py` (stays silent, Ctrl+C to stop) |
| 3. Test with MCP Inspector, over stdio | | `npx @modelcontextprotocol/inspector "$(which python)" "$(pwd)/server.py"`, then `--cli ... --method tools/list`, `--method tools/call --tool-name crm_search_clients --tool-arg query=lyon`, `--method resources/read --uri crm://clients/C-1003` |
| 4. Connect the server in Claude Code | | `claude mcp add orbis -- "$(which python)" "$(pwd)/server.py"`, then `claude mcp list` |
| 5. Serve over HTTP behind a token | `server.py`, `TODO(step 5)` | `export CRM_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"`, `python server.py --http`, then `curl -s -i -X POST http://127.0.0.1:8000/mcp -H 'Content-Type: application/json' -d '{}'` |
| 6. Test over HTTP with the Inspector | | `npx @modelcontextprotocol/inspector --cli http://127.0.0.1:8000/mcp --transport http --header "Authorization: Bearer $CRM_TOKEN" --method tools/list` |
| 7. Expose the server and call it through the MCP connector | `appel_connecteur.py`, `TODO(step 7)` | `cloudflared tunnel --url http://localhost:8000`, `export CRM_PUBLIC_URL="https://<random-words>.trycloudflare.com"`, `python server.py --http`, then `python appel_connecteur.py` |
| TypeScript variant | `ts/` | `cd ts && npm ci`, then `npx @modelcontextprotocol/inspector npx tsx src/stdio.ts`, `claude mcp add orbis-ts -- "$(pwd)/node_modules/.bin/tsx" "$(pwd)/src/stdio.ts"`, `npx tsx src/http.ts` (port 3000), `npx tsx src/appel_connecteur.ts` |

## Test it

```bash
bash test.sh
```

`test.sh` creates `.venv`, installs `requirements-dev.txt`, runs `npm ci` and the TypeScript type check in every `ts/` folder, compiles both starters and imports their server, then runs the tests against `solution/` and `solution-en/`. No API key, no AWS credentials, no tunnel and no Claude Code are needed.

What the tests cover:

- every primitive through the in-memory MCP client: tool schemas and annotations (read-only search, bounded `limit`, sector enum), the search with each filter, the `limit=99` validation error returned as `isError` (no traceback), the note written to the JSON file with today's date, the `ToolError` that says how to fix the call, the resource template and its `ResourceNotFoundError`, the prompt and the server instructions (steps 2 and 3);
- the Python server over stdio, launched as a subprocess the way the Inspector and Claude Code launch it (step 3);
- the Python server over Streamable HTTP: `401` without or with a wrong token, the exact `WWW-Authenticate` header, the protected resource metadata, `421` for an unknown host and `200` for the public tunnel host, plain JSON responses, and a full MCP session with the bearer token (steps 5 and 6);
- `appel_connecteur.py` with the real SDK against a mocked Messages API: `mcp_servers` with the token, the toolset deny list, the beta header, and the lesson's output lines (step 7);
- the TypeScript server, type-checked and driven over stdio and over HTTP by the Python MCP client;
- the optional Bedrock client (tool loop, deny list, errors sent back to the model) with botocore's `Stubber`;
- `cleanup.sh`, with a stand-in `claude` command.

Not covered offline: MCP Inspector itself (needs Node 22 and a browser for the UI), Claude Code, the cloudflared tunnel, and the real MCP connector call, which needs an API key and a public HTTPS URL.

To check your own work while you complete the TODOs:

```bash
LAB_TARGET=starter-en .venv/bin/python -m pytest tests      # or LAB_TARGET=starter
```

## Clean up

Nothing is created in the cloud. Three things stay open on your machine:

```bash
# 1. Stop the tunnel and the server: Ctrl+C in their terminals
# 2. Remove the servers from Claude Code (orbis, orbis-http, orbis-ts):
bash ../cleanup.sh
# 3. Forget the lab token:
unset CRM_TOKEN CRM_PUBLIC_URL
```

The quick tunnel URL stops existing as soon as `cloudflared` stops. Remove the servers from any other MCP host where you declared them.

## Swap the model

- **Another Claude model for step 7**: change `model=` in `appel_connecteur.py` (or `ts/src/appel_connecteur.ts`). The server does not depend on any model.
- **Amazon Bedrock (optional, not in the lesson)**: Bedrock's Converse API has no MCP connector, so `bedrock_mcp_client.py` is the MCP client itself. It starts `server.py` over stdio (no tunnel, no token), lists its tools, hands them to the model as Converse tools minus `crm_add_note` (the same deny list as the connector), runs each tool call on the server and sends the result back until the model answers.

  ```bash
  pip install -r ../requirements-bedrock.txt
  export BEDROCK_MODEL_ID="<a model id enabled in your account that supports tool use>"
  export AWS_REGION=eu-west-3
  MODEL_PROVIDER=bedrock python appel_connecteur.py     # or: python bedrock_mcp_client.py
  ```

  The output has the same shape as step 7: one `[call]` line per tool call, one `[result]` line, the answer and the stop reason. No model id is hard-coded.
