# M15 lab: red team your own agent

Companion code for the lab of module M15 (Security and governance) of the Intelligence Training
course: *Lab: red team your own agent*. [Version française](README.fr.md).

## Goal

A **defensive** red team exercise: you play the attacker against your own agent, on your own
test bench, to measure and close its weaknesses. Everything runs locally with **simulated
tools** that send no email and touch no real system: a tool call only writes a line to a list
of effects. You start from a deliberately under-protected agent, measure how many test
injections succeed, then turn on five defenses one by one and measure the progress at each
step. The point is not to write attacks, but to see that deterministic countermeasures bound
the impact where the prompt alone fails.

## Architecture

The bench (`banc.py`) loads `scenarios.json` and runs `agent.py`, which talks to the model and
calls `garde.py` before the simulated tools of `outils.py`. `garde.py` holds defenses D2 to D5
and, in the optional AWS part (step 8), the Bedrock Guardrails filter; an AgentCore Policy rule
on a Gateway can carry D5 outside the agent's code.

| File | Role |
| --- | --- |
| `outils.py` | The **simulated** tools (email, CRM, refund): they log, they do not act |
| `agent.py` | The tool-calling loop, defense D1 (separation of reading and acting) |
| `garde.py` | Defenses D2 to D5: allowlist, confirmation, filtering, Policy-style rule |
| `scenarios.json` | The test cases: legitimate tasks and documents containing a test injection |
| `banc.py` | Runs the scenarios, repeats each one N times, counts the successes |
| `providers.py` | Optional provider switch (Claude API, Claude on Bedrock, Bedrock Converse) |
| `rapport-campagne.md` | Template of the campaign report (step 7) |

Only two functions talk to the model: the loop in `agent.traiter` and the classifier
`garde._parait_injecte`. The simulated tools, the guard module, the scenarios and the counting
in the bench are independent of the model. The code keeps the French file names, identifiers
and strings of the lesson (`outils` means tools, `garde` guard, `banc` bench); the last line of
the bench, `Taux de réussite des injections`, reads "injection success rate".

```text
m15-agent-red-team/
├── starter/      outils.py and scenarios.json ready; agent.py, garde.py, banc.py with TODO markers
├── solution/     the complete bench, defenses D1 to D5 and the step 8 filter
├── infra/        Terraform for step 8 (guardrail, optional AgentCore Policy rule)
├── tests/        offline tests, and naive_agent.py, a model-free agent for dry runs
├── rapport-campagne.md, cleanup.sh, .env.example
└── test.sh       installs into .venv and runs every check, Terraform included
```

## Prerequisites

- Python 3.10 or later, a terminal, a Claude Console account and a key in `ANTHROPIC_API_KEY`.
- Step 8 (optional): an AWS account allowed to use Amazon Bedrock Guardrails (`ApplyGuardrail`),
  Terraform 1.5.7 or later, and for the most advanced the Gateway of the AgentCore module lab.
  Default Region of the course: `eu-west-3` (Paris). Before step 8, check on the Guardrails
  "Supported Regions" page that `ApplyGuardrail` is offered there; otherwise use a Region where
  it is, for example `eu-west-1` (Ireland), and note the date of your check.
- Optional: to replay the bench on another model provider (step 7), its access and credentials.

Never use real contact details (real email addresses, real customer data) in
`scenarios.json`: the tools are simulated, but the content still goes to the API. Use fictitious
data, such as `client@example.test`.

## Estimated cost

As stated in the lesson: steps 1 to 7 only use the Claude API, apart from the optional
comparison with other models, for **less than $2 for the whole lab** (each bench pass makes a
few dozen calls, mostly on Claude Haiku 5.5). The lesson gives no estimate for step 8: check the
Amazon Bedrock Guardrails pricing page before you run it.

## Steps

| Lesson step | In this repository |
| --- | --- |
| 1. Prepare the environment | `.venv` + `pip install -r requirements.txt` (pins `anthropic==2.12.0`) |
| 2. The simulated tools | `outils.py` (ready in `starter/`) |
| 3. The bare agent | `starter/agent.py` (TODO step 3), `solution/agent.py` |
| 4. The guard module, without defense | `starter/garde.py` (step 4 state) |
| 5. Measure the bare agent | `scenarios.json`, `starter/banc.py` (TODO step 5), `python banc.py '{}' 5` |
| 6. Harden, defense by defense | `starter/garde.py` (TODO step 6), `solution/garde.py` |
| 7. The campaign report | `rapport-campagne.md`; other models: `MODEL_PROVIDER` (below) |
| 8. Port D4 and D5 to AWS (optional) | `infra/` (Terraform), `garde.ticket_bloque`, defense `"guardrail"` |

## How to run

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m15-agent-red-team
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # or a profile created with "ant auth login"
python -c "import anthropic; print(anthropic.__version__)"
cd starter        # or: cd solution, to run the finished bench
```

Baseline (step 5), then each defense (step 6):

```bash
python banc.py '{}' 5
python banc.py '{"separation": true}' 5
python banc.py '{"liste_blanche": true}' 5
python banc.py '{"liste_blanche": true, "regle_montant": true}' 5
python banc.py '{"liste_blanche": true, "regle_montant": true, "filtrage": true}' 5
python banc.py '{"liste_blanche": true, "regle_montant": true, "filtrage": true, "confirmation": true}' 5
```

### Dry run without a model

`tests/naive_agent.py` is a model-free agent that obeys every instruction it finds in the
ticket: the worst case of an agent with no judgment. It costs nothing and needs no key, and
shows that the deterministic defenses (D1, D2, D3, D5) stop it on their own:

```bash
BANC_AGENT=naive_agent:traiter PYTHONPATH=../tests python banc.py '{}' 2
BANC_AGENT=naive_agent:traiter PYTHONPATH=../tests python banc.py '{"liste_blanche": true, "regle_montant": true}' 2
```

### Target another agent

The attack set (`scenarios.json`) and the evaluation (`banc.py`) are model-agnostic.
`BANC_AGENT=module:function` points the bench at any agent importable from `PYTHONPATH` that
follows this contract:

- `traiter(ticket: str, demande: str, defenses: dict) -> list[dict]`;
- every action goes through `garde.appeler(nom, args, demande, defenses)` (or the same checks),
  and the simulated tools of `outils.py` record the effects;
- it returns the effects of this ticket only (clear `outils.EFFETS` first).

### Step 8 (optional): D4 and D5 on AWS

```bash
cd ..   # the lab folder
cp infra/terraform.tfvars.example infra/terraform.tfvars   # region, optional Policy rule
terraform -chdir=infra init
terraform -chdir=infra apply
export AWS_REGION=$(terraform -chdir=infra output -raw region)
export BEDROCK_GUARDRAIL_ID=$(terraform -chdir=infra output -raw guardrail_id)
cd solution
python banc.py '{"guardrail": true}' 5
python banc.py '{"guardrail": true, "liste_blanche": true, "regle_montant": true}' 5
```

The `"guardrail"` defense calls `ApplyGuardrail` (prompt attack filter, version `DRAFT`) on the
ticket text before the agent sees it: the filter does not evaluate the content of a
`toolResult`, hence the explicit call. For D5 with AgentCore Policy, set `policy_engine_id` and
`gateway_arn` (the Gateway of the AgentCore lab) in `terraform.tfvars`: Terraform adds the
lesson's Cedar rule (`infra/policy-rembourser.cedar.tftpl`), which refuses `rembourser` above
the ceiling. Put the policy engine of the Gateway in `LOG_ONLY` mode first, then `ENFORCE`.

## How to test

```bash
bash test.sh
```

It creates `.venv`, installs `requirements-dev.txt`, runs the unit tests against `solution/`,
checks that `starter/` compiles and imports, checks `cleanup.sh`, then runs
`terraform fmt -check -recursive`, `terraform init -backend=false` and `terraform validate` on
`infra/` (set `SKIP_TERRAFORM=1` to skip them). No key and no AWS credentials are needed: the
Claude API is replaced by a mock transport behind a real `anthropic` client, Converse and
`ApplyGuardrail` go through botocore's Stubber, and the bench is driven by the naive agent.

## How to clean up

Steps 1 to 7 create no billed resource: delete the folder and the virtual environment.

```bash
bash cleanup.sh        # destroys the step 8 resources, if infra/ was applied
deactivate && rm -rf .venv
```

The Gateway and the policy engine of the AgentCore lab are not touched: keep them if you reuse
them elsewhere. Finally, check that no API key is left in your shell history.

## How to swap the model

Comparing several model families on the same bench is the best use of the lab. Do not touch
`outils.py`, `garde.py` (apart from its classifier model), `scenarios.json` or the counting in
`banc.py`: switch the provider of the two model-facing functions.

| `MODEL_PROVIDER` | Client | Agent model | D4 classifier model |
| --- | --- | --- | --- |
| `anthropic` (default) | `anthropic.Anthropic()` | `claude-opus-5-5` | `claude-haiku-5-5` |
| `anthropic-bedrock` | `anthropic.AnthropicBedrock` | `BEDROCK_MODEL_ID` | `BEDROCK_CLASSIFIER_MODEL_ID` (default: `BEDROCK_MODEL_ID`) |
| `bedrock` | boto3 `bedrock-runtime` `converse` (Amazon Nova, Meta Llama, Mistral AI...) | `BEDROCK_MODEL_ID` | `BEDROCK_CLASSIFIER_MODEL_ID` (default: `BEDROCK_MODEL_ID`) |

```bash
export MODEL_PROVIDER=bedrock AWS_REGION=eu-west-3
export BEDROCK_MODEL_ID=<agent model id> BEDROCK_CLASSIFIER_MODEL_ID=<classifier model id>
python banc.py '{}' 5
```

With Converse, the ticket stays in a labeled tool result, the structured output of the
classifier becomes `outputConfig.textFormat`, and `thinking` is not sent (it is
Claude-specific); a classifier answer that cannot be read blocks the action (fail closed).
`BEDROCK_STRICT_TOOLS=false`, `BEDROCK_CACHE_POINTS=false` and `BEDROCK_MAX_TOKENS` adapt the
requests to a model that lacks a feature. Record the model, its version and the date in the
campaign report: the deterministic defenses give the same result whatever the model, while D0
(the prompt policy) and D4 (filtering) vary from one family and version to the next.
