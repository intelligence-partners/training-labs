# M13 lab: the Acme support agent on Amazon Bedrock AgentCore

Companion code of the hands-on lab of module M13 (Amazon Bedrock AgentCore) of Intelligence
Training: the "fil rouge" support agent that assembles the whole module.
[Version française](README.fr.md)

You build the support agent of Acme, a fictitious online shop. It reads the status of orders,
opens tickets and refunds, but **never more than 50 euros**, and that limit does not depend on the
model. It remembers the preferences of each customer from one session to the next, and every
action is traced. You start from an "existing API", as in a real mission, without changing a line
of it.

## Architecture

You invoke the runtime `agent`, which reasons with Claude Opus 5.5 through the European inference
profile `eu.anthropic.claude-opus-5-5` and reads its memory. It calls the Gateway `tools`, whose
Policy engine decides on every call. The Gateway reads the API key from Identity and calls the Acme
HTTP API, served by a Lambda function. Traces and logs go to CloudWatch.

| Piece | Role in the lab |
| --- | --- |
| Runtime | Hosts the Strands agent (`SupportLab/app/agent/main.py`), one microVM per session |
| Memory | Keeps the history and extracts the preferences of each customer |
| Gateway | Exposes the Acme REST API as three MCP tools: `support___getOrder`, `support___createTicket`, `support___createRefund` |
| Identity | Keeps the API key in the token vault; the Gateway injects it in the `x-api-key` header |
| Policy | Allows reads and tickets, and refunds up to 5,000 cents |
| Observability | Traces, logs and decision metrics in CloudWatch |

Everything runs in **Paris (`eu-west-3`)**, where the lesson states that each of these pieces is
available on 27 October 2026.

The infrastructure is **Terraform** (`hashicorp/aws` 6.73.0), in two stacks: `terraform/acme-api`
(the existing API, as it would exist before the mission) and `terraform/support-agent` (runtime,
memory, Identity, Gateway, Policy, online evaluation). The AgentCore CLI is only used as a client
(`invoke`, `memory record list`, `runtime traces`, `runtime logs`, `eval ondemand`): nothing is
deployed with CDK or CloudFormation.

## Repository layout

```text
m13-agentcore-support-agent/
├── README.md, README.fr.md
├── .env.example              variables to adapt (region, model, names), no secret
├── test.sh                   offline checks (CI)
├── cleanup.sh                terraform destroy of both stacks, then what Terraform does not own
├── requirements-dev.txt      the agent's lock plus the test tools
├── tests/                    unit tests (fake model, local tools, Cedar engine) and Terraform checks
├── solution/
│   ├── acme-api/app.py       the existing API (step 1)
│   ├── SupportLab/
│   │   ├── app/agent/        main.py, gateway_client.py, memory/session.py (step 5),
│   │   │                     pyproject.toml and requirements.txt (pinned lock)
│   │   ├── schemas/          acme-support.template.json (step 3)
│   │   └── policies/         lecture, remboursement and b2b .template.cedar (step 7)
│   ├── terraform/
│   │   ├── acme-api/         main.tf, variables.tf, outputs.tf, versions.tf (step 1)
│   │   └── support-agent/    memory.tf (step 2), gateway.tf (steps 3 and 4), identity.tf (step 4),
│   │                         runtime.tf (step 6), policy.tf (step 7), online_eval.tf (step 10)
│   └── scripts/              check_api.sh, lab-env.sh, package_agent.sh, enable_transaction_search.sh
└── starter/                  the same tree, with TODO (step N) markers where you write the code
```

## Prerequisites

- A **sandbox** AWS account with administrator rights (the lab creates IAM roles) and an AWS budget
  configured (module M10).
- **AWS CLI v2**, configured: `aws sts get-caller-identity` answers.
- **Terraform 1.5.7 or later** (tested with 1.5.7; providers pinned in `versions.tf` and
  `.terraform.lock.hcl`).
- **Node.js 20.12 or later** and the AgentCore CLI, used as a client:
  `npm install -g @aws/agentcore@1.0.1` (the version these commands were checked with).
- **Python 3.10 or later and `uv`** (to build the CodeZip artifact; tested with uv 0.5.15), `jq`,
  `zip`, `curl`, `openssl`.
- Access to the Anthropic models in Amazon Bedrock: once per account, the use case form must have
  been submitted from the model catalog of the Bedrock console.

## Estimated cost

As stated in the lesson: the lab only creates pay-per-use resources, without commitment. The order
of magnitude is **a few dollars** for the whole lab if you clean up the same day, most of it being
Claude tokens (about twenty invocations, each with several model calls). The rest is marginal:
Runtime bills the CPU and memory consumed per second, Memory the events and records, Gateway and
Policy the calls, CloudWatch the ingestion; the Lambda function and the HTTP API usually stay in the
free tier. Prices change: check the AgentCore and Bedrock pricing pages before you start, and do not
skip the cleanup.

## Lesson steps in this repository

| Lesson step | What you run | Where the code is |
| --- | --- | --- |
| 1. Deploy the existing API | `terraform -chdir=terraform/acme-api apply`, `./scripts/check_api.sh` | `acme-api/app.py`, `terraform/acme-api/` |
| 2. The AgentCore project | nothing to run: the project is in `SupportLab/` | `SupportLab/app/agent/`, `terraform/support-agent/memory.tf` |
| 3. Describe the API in OpenAPI | Terraform writes the real server URL | `SupportLab/schemas/acme-support.template.json`, `terraform/support-agent/gateway.tf` |
| 4. Gateway, key and target | `terraform apply` (step 6) | `terraform/support-agent/identity.tf`, `gateway.tf` |
| 5. The agent code | `./scripts/package_agent.sh` | `gateway_client.py`, `main.py`, `memory/session.py` |
| 6. Deploy and test | `terraform apply -var enable_policy=false`, `agentcore invoke` | `terraform/support-agent/runtime.tf` |
| 7. The refund rule with Policy | `terraform apply`, scenario | `SupportLab/policies/`, `terraform/support-agent/policy.tf` |
| 8. Check the memory | `agentcore memory record list` | |
| 9. Observe | `agentcore runtime traces`, `agentcore runtime logs`, `aws cloudwatch list-metrics` | |
| 10. Evaluate (optional) | `terraform apply -var enable_online_eval=true`, `agentcore eval ondemand evaluate` | `terraform/support-agent/online_eval.tf` |
| Identity | `aws bedrock-agentcore-control list-api-key-credential-providers` | |
| Cleanup | `../cleanup.sh` | `cleanup.sh` |

## Deploy and test

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m13-agentcore-support-agent/solution     # or starter/
export AWS_REGION=eu-west-3
npm install -g @aws/agentcore@1.0.1

# Step 1: the existing API, protected by a key
export ACME_API_KEY=$(openssl rand -hex 24)
echo "$ACME_API_KEY" > .acme-api-key              # never commit it (git-ignored)
export TF_VAR_acme_api_key="$ACME_API_KEY"
terraform -chdir=terraform/acme-api init
terraform -chdir=terraform/acme-api apply
eval "$(./scripts/lab-env.sh)"                     # API_ID, API_URL, TF_VAR_acme_api_url
./scripts/check_api.sh                             # 401, then the order A-1042 "expédiée"

# Steps 5 and 6: build the CodeZip artifact, then deploy without Policy
./scripts/package_agent.sh                         # build/agent.zip, wheels for Linux arm64
./scripts/enable_transaction_search.sh             # once per account and Region (traces, step 9)
terraform -chdir=terraform/support-agent init
terraform -chdir=terraform/support-agent apply -var enable_policy=false
eval "$(./scripts/lab-env.sh)"                     # + RUNTIME_ARN, RUNTIME_ID, GATEWAY_ARN, MEMORY_ID

agentcore invoke --gateway "$GATEWAY_ARN" --path /mcp \
  --payload '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
agentcore invoke --runtime "$RUNTIME_ARN" \
  --session-id support-lab-session-0001-abcdefghijk \
  --payload '{"prompt":"Bonjour, où en est ma commande A-1042 ?","actorId":"c-4821"}'

# Step 7: attach the Policy engine and its three policies (enable_policy defaults to true)
terraform -chdir=terraform/support-agent apply
agentcore invoke --runtime "$RUNTIME_ARN" --session-id support-lab-session-0002-abcdefghijk \
  --payload '{"prompt":"Le colis A-1042 est arrivé abîmé. Remboursez-moi 120 euros.","actorId":"c-4821"}'
agentcore invoke --runtime "$RUNTIME_ARN" --session-id support-lab-session-0002-abcdefghijk \
  --payload '{"prompt":"Je confirme, 120 euros.","actorId":"c-4821"}'
agentcore invoke --runtime "$RUNTIME_ARN" --session-id support-lab-session-0002-abcdefghijk \
  --payload '{"prompt":"D accord, remboursez seulement 30 euros alors.","actorId":"c-4821"}'
agentcore invoke --gateway "$GATEWAY_ARN" --path /mcp --payload \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"support___createRefund","arguments":{"orderId":"A-1042","amountCents":12000,"reason":"colis endommagé"}}}'

# Step 8: memory (wait a few minutes for the extraction)
agentcore invoke --runtime "$RUNTIME_ARN" --session-id support-lab-session-0003-abcdefghijk \
  --payload '{"prompt":"Pour la suite, contactez-moi uniquement par courriel, jamais par téléphone.","actorId":"c-4821"}'
agentcore memory record list --id "$MEMORY_ID" --namespace /users/c-4821/preferences
agentcore invoke --runtime "$RUNTIME_ARN" --session-id support-lab-session-0004-abcdefghijk \
  --payload '{"prompt":"Comment allez-vous me tenir au courant pour mon remboursement ?","actorId":"c-4821"}'

# Step 9: observe
agentcore runtime traces list --id "$RUNTIME_ID" --since 30m
agentcore runtime traces get <trace-id> --id "$RUNTIME_ID"
agentcore runtime logs --id "$RUNTIME_ID" --since 30m
aws cloudwatch list-metrics --namespace AWS/Bedrock-AgentCore --metric-name DenyDecisions

# Step 10 (optional): online evaluation, then an immediate score of one session
terraform -chdir=terraform/support-agent apply -var enable_online_eval=true
agentcore eval ondemand evaluate --agent "$RUNTIME_ID" --evaluators Builtin.Helpfulness \
  --session-ids support-lab-session-0002-abcdefghijk --lookback-days 1

# What Identity does in this lab
aws bedrock-agentcore-control list-api-key-credential-providers
```

Session IDs must have at least 33 characters. With the **starter**, complete the `TODO (step N)`
blocks of each step before the corresponding `apply`, and run `package_agent.sh` again after every
change of the agent code (Terraform then uploads the new zip and updates the runtime).

> In this lab the customer identifier comes in the payload, which is enough to test. In production
> it must come from a verified identity, for example the `sub` claim of a JWT validated by the
> inbound authorizer of the runtime: otherwise any caller can read the memory of another customer.

Offline, without any AWS account:

```bash
./test.sh
```

It creates `.venv` from the agent's lock, runs the unit tests, checks the shell scripts
(`bash -n`, ShellCheck), then runs `terraform fmt -check`, `terraform init -backend=false` and
`terraform validate` on the four Terraform directories (solution and starter).

## Clean up

```bash
cd training-labs/labs/m13-agentcore-support-agent
./cleanup.sh               # or ./cleanup.sh starter, add --yes to skip the confirmation
```

The script destroys the support-agent stack, then the acme-api stack, deletes what AgentCore
created outside Terraform (the runtime's log groups, the evaluation results log group), removes
`.acme-api-key` and `build/`, then runs the checks of the lesson (runtimes, gateways, memories,
policy engines, API key providers, log groups) and exits non-zero if a lab resource is still there.
CloudWatch Transaction Search stays enabled for the account: its indexing beyond the free tier is
billed, lower the indexed percentage when you no longer need it (the script prints the command).
The lab creates no CDK bootstrap stack.

## Swap the model

AgentCore is framework- and model-agnostic. The agent reads its model from `MODEL_ID`:

```bash
aws bedrock list-inference-profiles --query 'inferenceProfileSummaries[].inferenceProfileId'
terraform -chdir=terraform/support-agent apply -var model_id=<profile id>
```

The runtime role follows the profile (Terraform reads the Regions it routes to from the profile).
To use another model provider, replace `BedrockModel` in `main.py` with another Strands model
provider; to use another framework, keep `BedrockAgentCoreApp` and the `@app.entrypoint` contract
(`{"prompt", "actorId"}` in, `{"result"}` out). Gateway, Policy, Identity and Memory do not change.

## What the offline checks cover

- The existing API: 401 without the key, the exact order JSON of step 1, tickets and refunds.
- The OpenAPI template: three operations, so three tools `support___*`, integer amount in cents,
  and every operation served by the API.
- The Cedar policies, evaluated with the Cedar engine (`cedarpy`): reads and tickets allowed, 3,000
  and 5,000 cents allowed, 5,001 and 12,000 denied by default, B2B denied by the `forbid`.
- The agent, with the pinned Strands Agents and AgentCore SDKs and a scripted fake model: payload
  validation, the tool loop, a refused refund handled as a normal tool result, one agent per session
  and actor, and the HTTP contract of the runtime (`/ping`, `/invocations`) through the real SDK app.
- The Gateway client (SigV4 for `bedrock-agentcore`, `/mcp` endpoint) and the memory session
  (namespaces per actor, threshold 0.3, each namespace filled by a Terraform strategy).
- The Terraform code: names and settings of the lesson, least-privilege statements, pinned
  providers; `terraform validate` against the pinned provider schema.
- The packaging script was run locally: it produces a 38 MB zip with Linux arm64 wheels.

What only a real deployment can show: model access, the answers of the agent, the Gateway calls with
the injected key, the decisions of the Policy engine (and its validation of the policies against the
tool schema), the memory extraction, the traces, the online evaluation, and the AgentCore CLI client
commands against real resources (they were checked offline up to credential loading only).

## Notes on the Terraform code

- The project files are in `SupportLab/` and Terraform creates every resource. The memory
  reproduces the four strategies of the `agent-python-strands` template of AgentCore CLI 1.0.1
  (semantic, preferences, summary, episodic). The CLI, used here only as a client, is pinned to
  1.0.1: version 1.2.0 generates only two strategies and a threshold of 0.0, and the lesson's
  `/users/c-4821/preferences` check relies on the 1.0.x behaviour.
- Resource names carry the project prefix `supportlab` (the CLI also prefixes them with the
  project name): runtime `supportlab_agent`, memory `supportlab_agentMemory`, Gateway
  `supportlab-tools`, key provider `supportlab-acme`, engine `supportlab_guard`. The target
  (`support`), the tool names and the policy names are those of the lesson.
- The IAM roles mirror what the AgentCore CLI constructs grant, with Bedrock access narrowed to the
  inference profile and its destination models. The functions write to their own log group only,
  instead of the `AWSLambdaBasicExecutionRole` managed policy.
- The API key is in the Terraform state (local, git-ignored). In production, reference a Secrets
  Manager secret (`api_key_secret_config`) or use `api_key_wo` with Terraform 1.11 or later.
- The Terraform state stays local (`terraform/*/terraform.tfstate`, git-ignored).
