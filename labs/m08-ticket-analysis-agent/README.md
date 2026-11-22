# M08 lab: ticket analysis agent

Companion code for the lab of module M08 (Agents) of the Intelligence Training course:
*Lab: a ticket analysis agent with guardrails*. [Version française](README.fr.md).

## Goal

Build, end to end, a level-1 support agent that reads open tickets, searches a knowledge
base, sets a priority, writes a draft reply and escalates when it must, then try to break it:
a booby-trapped ticket (T-1005 contains a prompt injection), an unattended run, a budget that
is too short, an invalid identifier. You end up with a production agent skeleton you can port to
the Tool Runner, the Agent SDK or Managed Agents.

## Architecture

The agent runs on your machine, in Python, and calls the Claude API with `claude-opus-5-5`.
`agent.py` holds the bounded loop; `tools.py` holds six typed tools that read and write local
files in `data/`. Three tools read (`list_tickets`, `get_ticket`, `search_kb`), three write
(`set_priority`, `save_draft`, `escalate`); `set_priority` and `escalate` are visible to other
teams and wait for your approval at the terminal. Every tool call and decision goes to
`audit.jsonl`.

| Guardrail | Where it lives |
| --- | --- |
| Strict schemas and enums | Tool definitions (`strict: true`, `enum`) |
| Business validation (id format, length, existence) | `tools.py` functions, `ToolInputError` |
| Customer content tagged as data | `get_ticket` and the system prompt |
| Human approval, refuse by default when unattended | `approuver()` in `agent.py`, `--auto-refus` |
| Loop bounded in turns and dollars | `MAX_TOURS`, `--budget` |
| Audit log | `audit.jsonl` |

The code keeps the lesson's French identifiers, prompts, tickets and printed messages
(`approuver` means approve, `tours` turns, `rapport` report), so that the lesson's commands,
expected outputs and checks work unchanged. Comments are in English.

```text
m08-ticket-analysis-agent/
├── starter/      code to complete (TODO markers per lesson step), same data
├── solution/     complete code: agent.py, tools.py, providers.py, data/
├── tests/        offline tests (Claude API and Bedrock mocked)
├── requirements.txt, requirements-dev.txt, .env.example
└── test.sh       installs into .venv and runs every check
```

## Prerequisites

- Python 3.10 or later, a terminal, an editor.
- A Claude API key created in the Console (platform.claude.com) with available credit. Create
  one for the lab only; you will revoke it at the end.
- No AWS service: this lab creates no cloud resource (unless you choose the optional Bedrock
  provider below).

## Estimated cost

As stated in the lesson: a full run on the five tickets takes about 10 to 15 turns; allow a few
tens of cents to one dollar depending on the number of turns, the length of the answers and the
effect of the cache. The script stops on its own above $1 by default. The prices coded in the
script ($4 per million input tokens and $20 per million output tokens for Claude Opus 5.5) are
those of the date of writing: check the pricing page.

## Steps

| Lesson step | In this repository |
| --- | --- |
| 1. Prepare the project | `python3 -m venv .venv`, `pip install -r requirements.txt` (pins `anthropic==2.12.0`) |
| 2. The data | `data/tickets.json`, `data/kb.json`, and the reset copy `data/tickets.init.json` (provided) |
| 3. The tools | `starter/tools.py` (TODO step 3), `solution/tools.py` |
| 4. The loop and its guardrails | `starter/agent.py` (TODO step 4), `solution/agent.py` |
| 5. First run | `python agent.py "Traite les tickets ouverts."` |
| 6. Test the guardrails | `--auto-refus`, `--budget 0.03`, invalid id T-12 (commands below) |
| 7. Going further (optional) | Tool Runner, evaluation, Managed Agents, escalation cap: not in the repository |

## How to run

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m08-ticket-analysis-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # your lab key
python -c "import anthropic; print(anthropic.__version__)"
cd starter        # or: cd solution, to run the finished agent
```

Step 3, check the tools without calling the model:

```bash
python -c "import json, tools; print(json.dumps(tools.list_tickets('open'), ensure_ascii=False)[:70])"
python -c "import tools; print([r['id'] for r in tools.search_kb('erreur 401 SSO')['results']])"
python -c "import tools; tools.get_ticket('T-12')"
```

Steps 5 and 6:

```bash
python agent.py "Traite les tickets ouverts."
# reset between two runs
cp data/tickets.init.json data/tickets.json && rm -rf drafts escalations.jsonl audit.jsonl
python agent.py --auto-refus "Traite les tickets ouverts."
grep -c '"decision": "refusé"' audit.jsonl
python agent.py --budget 0.03 "Traite les tickets ouverts." ; echo "code de sortie : $?"
tail -n 1 audit.jsonl
python agent.py "Ouvre le ticket T-12 puis le ticket T-1003 et propose une réponse."
grep '"decision": "invalide"' audit.jsonl
```

Exit codes: 0 report written, 1 unexpected `stop_reason`, 2 budget reached, 3 turn limit.

## How to test

```bash
bash test.sh
```

It creates `.venv`, installs `requirements-dev.txt`, runs the unit tests against `solution/`
and checks that `starter/` compiles and imports. The tests need no key and no network: the
Claude API is replaced by a mock transport behind a real `anthropic` client (so every request
is still validated by the SDK), and Converse calls go through botocore's Stubber.

## How to clean up

This lab creates no AWS resource and no persistent object on the Anthropic side: nothing keeps
being billed once the script stops.

```bash
deactivate
cd ../.. && rm -rf m08-ticket-analysis-agent/.venv   # or remove your clone
```

Then revoke the lab API key in the Console (API keys page) and remove it from your shell
(`unset ANTHROPIC_API_KEY`).

## How to swap the model

The lesson's path is the Claude API with `claude-opus-5-5`. `providers.py` adds an optional
switch, `MODEL_PROVIDER`, that keeps `agent.py` and `tools.py` unchanged:

| `MODEL_PROVIDER` | Client | Model id |
| --- | --- | --- |
| `anthropic` (default) | `anthropic.Anthropic()` | `claude-opus-5-5` |
| `anthropic-bedrock` | `anthropic.AnthropicBedrock` (Claude on Amazon Bedrock) | `BEDROCK_MODEL_ID` |
| `bedrock` | boto3 `bedrock-runtime` `converse` (any Bedrock model with tool use) | `BEDROCK_MODEL_ID` |

```bash
export MODEL_PROVIDER=bedrock AWS_REGION=eu-west-3
export BEDROCK_MODEL_ID=<a model or inference profile id enabled in your account>
export PRICE_SHEET='{"input": ..., "output": ..., "cache_write": ..., "cache_read": ...}'
python agent.py --auto-refus "Traite les tickets ouverts."
```

- Set `PRICE_SHEET` to the prices of the model you run (dollars per million tokens): the cost
  estimate and the `--budget` guardrail depend on it.
- With `bedrock`, requests are translated to Converse: tools keep `strict`, `cache_control`
  becomes a cache point, `effort` is Claude-specific and is not sent. For a model that lacks a
  feature, set `BEDROCK_STRICT_TOOLS=false`, `BEDROCK_CACHE_POINTS=false` or
  `BEDROCK_MAX_TOKENS`. Without strict tool use, the schema no longer guarantees the shape of
  the arguments: the business validation in `tools.py` still applies, but a missing argument
  stops the script.
- Bedrock providers need AWS credentials allowed to invoke the model; they create no resource.
