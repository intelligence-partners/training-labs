# M14 lab: cost and quality dashboard for an agent

Companion code for the lab of module M14 (LLMOps) of the Intelligence Training course:
*Lab: cost and quality dashboard for an agent*. [Version française](README.fr.md).

## Goal

Build the cockpit of a ticket triage agent that runs on Claude Opus 5.5 through Amazon Bedrock:
OpenTelemetry traces to CloudWatch, a cost per task computed from the `usage` counters, quality
and cost metrics, an evaluation set of eight tickets, a dashboard, three alarms and a budget.
Then ship a deliberately faulty prompt (`v2`) and check that the setup detects the cost
regression, locates it and gets it fixed. Allow one hour.

## Architecture

Three flows leave the agent (`agent.py`, on your machine): inference to Bedrock (streaming,
`AnthropicBedrock` client, `bedrock-runtime` endpoint, Region eu-west-3, inference profile
`eu.anthropic.claude-opus-5-5`), spans over OTLP to the X-Ray endpoint (ADOT, Transaction
Search, `aws/spans`), and business metrics to CloudWatch (`M14/AgentSupport`, with and without
the `PromptVersion` dimension). Bedrock adds its `AWS/Bedrock` metrics and its invocation logs.
Three alarms notify an SNS topic, then an email; AWS Budgets also sends an email.

The agent, its prompt, its tools, its tickets and its metric names stay in French, as in the
lesson (`TacheReussie` means successful task, `CoutTacheUSD` task cost, `TokensLusEnCache`
tokens read from the cache), so that the lesson's commands, dashboard, alarms and checks work
unchanged. Comments are in English.

```text
m14-llmops-cost-quality-dashboard/
├── starter/       agent.py to complete (TODO markers for step 5), verifier.py, providers.py
├── solution/      agent.py (instrumented agent), verifier.py (step 2), providers.py
├── infra/         Terraform for steps 3, 4, 8, 9 and 10 (hashicorp/aws pinned to 6.72.0)
├── otel.env       ADOT variables of step 6
├── cleanup.sh     lesson cleanup (terraform destroy and the steps Terraform does not cover)
├── tests/         offline tests (Bedrock, CloudWatch, Converse and spans mocked)
└── test.sh        installs into .venv and runs every check, Terraform included
```

The lesson creates the AWS resources with AWS CLI commands and JSON files; this repository
provisions the same resources, with the same names and settings, with Terraform. Both paths end
in the same account state; use one of them, not both.

| Lesson file or command | Terraform (`infra/`) |
| --- | --- |
| Step 3: log group, `confiance-bedrock.json`, `ecrire-journaux.json`, `journalisation.json` | `invocation_logging.tf` |
| Step 4: `transaction-search.json`, `update-trace-segment-destination` | `transaction_search.tf` (if `enable_transaction_search`) |
| Step 8: `tableau.json`, `put-dashboard` | `dashboard.tf`, `tableau.json.tftpl` |
| Step 9: SNS topic and subscription, `alarme-cout.json`, `alarme-reussite.json`, `alarme-cache.json` | `alarms.tf` (the cache alarm is the exercise solution) |
| Step 10: `budget.json`, `notifications.json` | `budget.tf` |

## Prerequisites

- A **sandbox AWS account**, never production, and an AWS CLI v2 profile with administrator
  rights on that account.
- Permission to invoke Claude Opus 5.5 in Bedrock from eu-west-3 (the module M12 lab details
  model access).
- Python 3.10 or later, Terraform 1.5.7 or later, and an email address for notifications.
- An AWS console open on the eu-west-3 Region.

## Estimated cost

As stated in the lesson:

| Item | Estimate |
| --- | --- |
| Claude Opus 5.5 inference (three runs of eight tasks, one of them without cache) | $1 to $3 depending on current Bedrock pricing |
| Custom metrics and alarms | a few cents, prorated (the free tier covers 10 metrics and 10 alarms) |
| Dashboard | free up to 3 custom dashboards |
| Invocation logs and spans | a few megabytes, under $0.10 |
| Budget without actions | free |

Expect **less than $5** if you do the cleanup at the end.

## Steps

| Lesson step | In this repository |
| --- | --- |
| 1. Prepare the environment | `.venv` + `pip install -r requirements.txt` (pinned versions) |
| 2. Check model access | `python verifier.py` |
| 3. Enable invocation logging | `infra/invocation_logging.tf` |
| 4. Enable Transaction Search | `infra/transaction_search.tf`, variable `enable_transaction_search` |
| 5. Write the instrumented agent | `starter/agent.py` (TODO step 5), `solution/agent.py` |
| 6. Run v1 with ADOT | `source ../otel.env`, then `PROMPT_VERSION=v1 opentelemetry-instrument python agent.py` |
| 7. Read a trace | CloudWatch console, Transaction Search, service `agent-support-m14` |
| 8. The dashboard | `infra/dashboard.tf`, variable `model_id_observe` |
| 9. The SNS topic and three alarms | `infra/alarms.tf`, variables `alert_email`, `cost_alarm_threshold` |
| 10. The budget | `infra/budget.tf` |
| 11. Ship the faulty version | `PROMPT_VERSION=v2 opentelemetry-instrument python agent.py` |
| 12. Roll back and measure | `PROMPT_VERSION=v1 opentelemetry-instrument python agent.py` |

## How to run

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m14-llmops-cost-quality-dashboard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export AWS_PROFILE=<your sandbox profile> AWS_REGION=eu-west-3
aws sts get-caller-identity --query Account --output text
(cd solution && python verifier.py)     # step 2: end_turn ['prêt'] ...
```

### Before you apply (steps 3 and 4)

Bedrock keeps one invocation logging configuration per account and Region, and applying
`infra/` replaces it. Save the current one first; `cleanup.sh` restores it at the end:

```bash
aws bedrock get-model-invocation-logging-configuration --query loggingConfig --output json \
  > infra/previous-logging-config.json
aws xray get-trace-segment-destination
```

If the X-Ray destination is already `CloudWatchLogs` with the `ACTIVE` status, set
`enable_transaction_search = false`: the lab then leaves Transaction Search alone, and the
cleanup does not disable it.

### Provision (steps 3, 4, 8, 9, 10)

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars   # set alert_email and enable_transaction_search
terraform -chdir=infra init
terraform -chdir=infra apply
```

Confirm the SNS subscription from the email you receive. After the first v1 run (step 6), set
`cost_alarm_threshold` to twice the average cost per task you noted, and `model_id_observe` to
the value returned by the command below, then run `terraform -chdir=infra apply` again:

```bash
aws cloudwatch list-metrics --namespace AWS/Bedrock --metric-name Invocations \
  --query 'Metrics[].Dimensions[?Name==`ModelId`].Value' --output text
```

### Run the agent (steps 6, 11, 12)

```bash
cd solution          # or starter, once its TODO markers are done
source ../otel.env
PROMPT_VERSION=v1 opentelemetry-instrument python agent.py
PROMPT_VERSION=v2 opentelemetry-instrument python agent.py   # step 11: the faulty version
PROMPT_VERSION=v1 opentelemetry-instrument python agent.py   # step 12: rollback
aws cloudwatch describe-alarms --alarm-name-prefix m14- \
  --query 'MetricAlarms[].[AlarmName,StateValue]' --output table
```

If a call appears twice in the traces, another instrumentation already traces the SDK: run
again with `ANTHROPIC_OPEN_TELEMETRY=false`.

## How to test

```bash
bash test.sh
```

It creates `.venv`, installs `requirements-dev.txt`, runs the unit tests against `solution/`,
checks that `starter/` compiles and imports, checks the shell scripts, then runs
`terraform fmt -check -recursive`, `terraform init -backend=false` and `terraform validate` on
`infra/` (set `SKIP_TERRAFORM=1` to skip them). No AWS credentials are needed: the Bedrock calls
go to a mock transport behind a real Anthropic SDK client, CloudWatch and Converse calls go
through botocore's Stubber (validated against the service models), and spans go to an
in-memory exporter. The tests also check that every metric read by the dashboard and the alarms
is a metric the agent publishes.

## How to clean up

```bash
bash cleanup.sh        # or AUTO_APPROVE=1 bash cleanup.sh
deactivate && rm -rf .venv
```

`cleanup.sh` runs `terraform destroy` (budget, alarms, dashboard, SNS topic and its
subscription, invocation logging, log group, IAM role, Transaction Search resource policy),
then, only if the lab enabled Transaction Search, switches X-Ray back to `XRay` and deletes
`aws/spans` (Terraform does not change X-Ray on destroy). If you saved a previous Bedrock logging
configuration, it restores it. The `M14/AgentSupport` custom metrics cannot be deleted: they
stop being fed, their prorated hourly billing stops, and they disappear from the console on
their own.

## How to swap the model

- **Another Claude model or inference profile on Bedrock**: set `MODEL_ID` (the lesson's
  variable), and `model_id_observe` for the dashboard.
- **Another model family on Bedrock** (Amazon Nova, Meta Llama, Mistral AI...): set
  `MODEL_PROVIDER=bedrock` and `MODEL_ID` to a model id enabled in your account. The agent then
  goes through the boto3 `bedrock-runtime` Converse API, through `providers.py`, without code
  changes. Set `PRICE_SHEET` to that model's prices, or the costs and the cost alarm are wrong:

  ```bash
  export MODEL_PROVIDER=bedrock MODEL_ID=<model id>
  export PRICE_SHEET='{"input": ..., "cache_write": ..., "cache_read": ..., "output": ...}'
  ```

  With Converse, `cache_control` becomes a cache point, tools keep `strict`, and `effort` is not
  sent (it is Claude-specific); `BEDROCK_CACHE_POINTS=false`, `BEDROCK_STRICT_TOOLS=false` and
  `BEDROCK_MAX_TOKENS` adapt the request to a model that lacks a feature. The adapter calls
  `Converse`, not `ConverseStream`, so the `AWS/Bedrock` `TimeToFirstToken` metric is not fed in
  that mode.
- To compare two families on the same dashboard, as the lesson suggests in "Going further",
  add a model dimension to the business metrics in `publier()`: this repository does not.
