# M10 lab: your first serverless service

Companion code for the lab of module M10 (AWS foundations) of Intelligence Training: a **prompt registry**, the API where a team stores its prompt templates and reads them back by ID. Version française : [README.fr.md](README.fr.md).

The infrastructure is written in **Terraform** (HCL), with the `hashicorp/aws` provider pinned to an exact version.

## Goal and architecture

An API Gateway **HTTP API** exposes two routes, `POST /prompts` and `GET /prompts/{id}`. Both invoke one **Lambda** function in Python 3.13 on Graviton (`arm64`), which writes to and reads from an on-demand **DynamoDB** table. The function writes JSON logs to a **CloudWatch Logs** group retained for 7 days, and its execution role allows nothing else: `dynamodb:PutItem` and `dynamodb:GetItem` on this table, `logs:CreateLogStream` and `logs:PutLogEvents` on this log group. The API is throttled to 5 requests per second with bursts of 10. Everything is deployed in `eu-west-3` and tagged `Projet=formation-m10`, `Environnement=lab`.

```
labs/m10-first-serverless-service/
├── starter/            what you start from (the registre-prompts project, with TODOs)
│   ├── src/app.py
│   └── infra/          providers.tf, variables.tf, main.tf, outputs.tf
├── solution/           the complete, working project
│   ├── src/app.py      the function (handler app.handler)
│   └── infra/          providers.tf, variables.tf, main.tf, outputs.tf, .terraform.lock.hcl
├── tests/              offline tests: handler (DynamoDB mocked by moto), offline terraform plan
├── test.sh             runs every offline check
├── cleanup.sh          terraform destroy, then checks that nothing is left
└── .env.example
```

| Resource (Terraform address) | Role |
| --- | --- |
| `aws_dynamodb_table.prompts` | Table `registre-prompts`, on demand, key `id` |
| `aws_cloudwatch_log_group.prompts` | `/aws/lambda/registre-prompts-prompts`, 7 days |
| `aws_iam_role.prompts_function`, `aws_iam_role_policy.minimal` | Execution role, inline policy `registre-prompts-minimal`, no managed policy |
| `aws_lambda_function.prompts` | Function `registre-prompts-prompts`, python3.13, arm64, 256 MB, 10 s, JSON logs at INFO |
| `aws_apigatewayv2_api.prompts`, `aws_apigatewayv2_stage.default`, `aws_apigatewayv2_integration.prompts`, `aws_apigatewayv2_route.*` | HTTP API, `$default` stage, two routes |
| `aws_lambda_permission.*` | API Gateway may invoke the function, for these two routes only |

The JSON field names (`nom`, `texte`, `creeLe`, `erreur`), the error messages and the `prompt_cree` log event stay in French: the course checkpoints rely on them.

## Prerequisites

- An AWS account secured as described in the IAM lesson (MFA on the root user, which you do not use here) and a budget with an alert, as described in the cost lesson.
- An administrator identity on your learning account: the lab creates an IAM role, which the `PowerUserAccess` managed policy does not allow.
- Temporary credentials in the CLI: an `aws configure sso` profile (Identity Center) or `aws login` (AWS CLI 2.32.0 or later). No long-term access keys.
- **AWS CLI v2** and **Terraform 1.5.7 or later** (`aws --version`, `terraform version`). Terraform downloads the provider (`hashicorp/aws` 6.72.0, `hashicorp/archive` 2.8.1) on `terraform init`.
- To run the offline tests only: Python 3.10 or later.
- If your account is on the free plan, check the Free Tier FAQ to confirm that Lambda, API Gateway, DynamoDB and CloudWatch are available on it.

## Estimated cost

As the lesson states it: no resource in this lab is billed by the hour: no NAT gateway, no interface endpoint, no instance. Everything is billed by usage: API Gateway requests, Lambda requests and GB-seconds, on-demand DynamoDB requests and storage, log ingestion and storage. For the hundred or so requests of the lab, the bill comes to **fractions of a cent**, and it can be zero within the Free Tier limits. It only stays negligible if you do the final **cleanup**. For a precise estimate, use the AWS Pricing Calculator. (With Terraform, the code is uploaded directly to Lambda: there is no artifact bucket in S3.)

## Steps (mapped to the lesson)

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m10-first-serverless-service/starter   # or solution/ to deploy the finished lab
```

| Lesson step | In this repo |
| --- | --- |
| 1. Check your identity and Region | `export AWS_PROFILE=lab AWS_REGION=eu-west-3` then `aws sts get-caller-identity` (never `root`) |
| 2. Create the project | `starter/` is the `registre-prompts` project: complete the TODOs of `src/app.py`, `infra/main.tf` and `infra/outputs.tf` |
| 3. Validate and build | `cd infra && terraform fmt -check && terraform init && terraform validate` |
| 4. Deploy | `terraform plan -out=tfplan`, read the plan (12 to add), then `terraform apply tfplan` |
| 5. Test the API | `API_URL=$(terraform output -raw api_url)`, then the lesson's `curl` commands |
| 6. Read the logs | `aws logs tail /aws/lambda/registre-prompts-prompts --since 10m --region eu-west-3` |
| 7. Check least privilege | the lesson's commands, unchanged (function `registre-prompts-prompts`, policy `registre-prompts-minimal`) |
| 8. Track the cost by tag (optional) | Cost Explorer, filter `Projet = formation-m10` |
| Cleanup | `bash cleanup.sh` (see below) |

## Deploy

From the `infra/` folder of the project you deploy (`starter/infra` once completed, or `solution/infra`):

```bash
export AWS_PROFILE=lab AWS_REGION=eu-west-3
aws sts get-caller-identity
terraform init
terraform validate
terraform plan -out=tfplan      # read it: 12 resources to add, nothing to change or destroy
terraform apply tfplan          # ends with "Apply complete! Resources: 12 added, 0 changed, 0 destroyed."
terraform output                # api_url, function_name, table_name
```

The plan is your change set: read it before applying. It lists `aws_iam_role`, `aws_iam_role_policy`, `aws_lambda_function`, `aws_dynamodb_table`, `aws_cloudwatch_log_group`, `aws_apigatewayv2_api`, `aws_apigatewayv2_stage`, `aws_apigatewayv2_integration`, two `aws_apigatewayv2_route` and two `aws_lambda_permission`; no NAT gateway, no IAM user. The routes declare `authorization_type = "NONE"`: the API is public, which is acceptable for this throttled lab deleted within the hour, never for a real service (IAM, JWT or Lambda authorization).

Try it:

```bash
API_URL=$(terraform output -raw api_url)
curl -s -X POST "$API_URL/prompts" -H "Content-Type: application/json" \
  -d '{"nom": "resume-contrat", "texte": "Résume le contrat ci-dessous en cinq points, en citant les articles."}'
curl -s "$API_URL/prompts/<id returned above>"
curl -s -i -X POST "$API_URL/prompts" -H "Content-Type: application/json" -d '{"nom": "sans-texte"}'   # 400
aws logs tail /aws/lambda/registre-prompts-prompts --since 10m --region eu-west-3
```

## Test (offline)

```bash
bash test.sh                      # the solution
LAB_TARGET=starter bash test.sh   # your work in starter/ (fails until every TODO is done)
```

`test.sh` needs no AWS account and makes no AWS call. It creates `.venv`, then runs:

- `terraform fmt -check -recursive`, `terraform init -backend=false` and `terraform validate` on `solution/infra` and `starter/infra`;
- the unit tests of the handler (`tests/test_handler.py`), with DynamoDB mocked by moto: status codes, the exact French messages, length limits, base64 bodies, the `prompt_cree id=… taille=…` log line without the prompt text, and the fact that the code calls only `PutItem` and `GetItem`;
- checks on an offline `terraform plan` (`tests/test_infra.py`): fake credentials, every AWS endpoint pointed at a closed local port. They assert the runtime, architecture, memory, timeout, JSON logging, 7-day retention, throttling, routes, the exact actions of the execution role, the absence of managed policies and the cost tags.

What only a real deployment can verify: the actual invocation through API Gateway, IAM propagation, the content of CloudWatch logs, and the `429` answers above the throttling limit.

## Clean up

```bash
bash cleanup.sh            # from the lab folder; or: bash cleanup.sh path/to/registre-prompts
bash cleanup.sh --yes      # without Terraform's confirmation prompt
```

The script runs `terraform destroy` (table and data, function, API, role, log group), then checks that the function, the table and the `/aws/lambda/registre-prompts` log groups no longer exist, and deletes the local build artifact (`infra/.build`) and saved plan. By hand, the equivalent is `terraform destroy` in `infra/`, then:

```bash
aws lambda get-function --function-name registre-prompts-prompts --region eu-west-3          # ResourceNotFoundException
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/registre-prompts --region eu-west-3   # "logGroups": []
```
