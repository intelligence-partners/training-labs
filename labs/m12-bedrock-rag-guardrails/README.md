# M12 lab: a RAG assistant on Amazon Bedrock, with Knowledge Bases and Guardrails

Companion code of the hands-on lab of module M12 (Amazon Bedrock) of Intelligence Training.
[Version française](README.fr.md)

You build, in your own AWS account in Paris (`eu-west-3`), an internal HR assistant: an employee
asks a question over HTTP, a Lambda function retrieves the useful passages from a Knowledge Base,
Claude Opus 5.5 writes the answer, and a guardrail filters the question and the answer. The lab
takes about 75 minutes and ends with a complete cleanup.

## Goal

A `POST` on your API returns a JSON object with the answer (`reponse`), the source documents
(`sources`), the stop reason (`stopReason`) and the guardrail verdict (`guardrail`). Five behaviours
must be observed:

1. a question covered by the documents gets a correct answer, with its source;
2. an answer that contains a phone number has it masked;
3. a jailbreak attempt is blocked on input;
4. a request for individual legal advice is refused;
5. a question outside the documents does not get an invented answer.

The JSON keys and verdicts (`aucun`, `masqué`, `bloqué`) stay in French: the checkpoints of the
lesson read them.

## Architecture

Employees call an **HTTP API** (Amazon API Gateway, quick create). The API invokes the **Lambda
function** `lab-rag-rh`, which:

1. calls **Retrieve** on the Knowledge Base `kb-lab-rh` (4 passages). The base is fed from the
   bucket `lab-rag-rh-<account>` and stores its vectors (Titan Text Embeddings V2, 1,024 dimensions)
   in an **OpenSearch Serverless** collection;
2. calls the **Converse** API with the inference profile `eu.anthropic.claude-opus-5-5`, the passages
   qualified as the grounding source and the question as the query, under the guardrail
   `lab-rag-rh` (Classic tier) on input and output.

Logs and traces go to CloudWatch. The design choices come from the lesson: a vector store you
manage (OpenSearch Serverless), no reranking, Retrieve then Converse rather than
RetrieveAndGenerate (to control the prompt and qualify the guardrail blocks), and the Classic
guardrail tier.

All the infrastructure is **Terraform** (`hashicorp/aws` 6.73.0). Two steps stay CLI calls because
they are actions, not resources: the ingestion job (step 3) and the tests.

## Repository layout

```text
m12-bedrock-rag-guardrails/
├── README.md, README.fr.md
├── .env.example            variables to adapt (region, model, names), no secret
├── test.sh                 offline checks (CI)
├── cleanup.sh              terraform destroy, then checks that nothing is left
├── requirements-dev.txt    pinned versions for the offline checks
├── tests/                  unit tests (AWS calls stubbed) and static Terraform checks
├── solution/               the complete lab
│   ├── docs/               the three documents and their .metadata.json files (step 1)
│   ├── lambda/app.py       the function (step 6)
│   ├── index_builder/      helper function that creates the vector index (step 2)
│   ├── terraform/          versions.tf, variables.tf, s3.tf (step 1), opensearch.tf and
│   │                       knowledge_base.tf (step 2), guardrail.tf (step 5), lambda.tf (step 6),
│   │                       api.tf (step 7), outputs.tf
│   └── scripts/            00-check-model.sh, lab-env.sh, 03-sync.sh ... 08-test-behaviours.sh
└── starter/                the same tree, with TODO (step N) markers where you write the code
```

## Prerequisites

- A **test** AWS account where you are administrator, with access to the Anthropic models open
  (the use case form submitted once, see the first lesson of the module).
- Region **eu-west-3** (Paris).
- **AWS CLI v2**, configured: `aws sts get-caller-identity` answers.
- **Terraform 1.5.7 or later** (the code is tested with 1.5.7; providers pinned in
  `versions.tf` and `.terraform.lock.hcl`).
- `curl` and `jq`.
- For the offline checks only: Python 3.10 or later (the CI uses 3.12).

## Estimated cost

As stated in the lesson:

| Item | Estimate |
| --- | --- |
| OpenSearch Serverless collection | the Bedrock documentation does not specify the generation of the collection created by quick create: count the classic case, at least 1 indexing OCU and 1 search OCU, billed even without any request, at about $0.24 per OCU-hour in us-east-1 (check the Paris price), that is about $0.50 per hour and in the order of $350 per month if it stays in place. A next-generation group can go down to 0 OCU when idle, but do not count on it here |
| Claude Opus 5.5 | about thirty requests of a few thousand tokens: less than one dollar |
| Titan embeddings, guardrail | a few cents |
| Lambda, API Gateway, S3, CloudWatch | negligible, often covered by the free tier |
| **Total if you clean up the same day** | **less than $5** |

> Create an AWS Budgets alert at $10 on the account before you start, and never end a work
> session without the cleanup: a forgotten classic OpenSearch Serverless collection costs in the
> order of $350 per month.

## Lesson steps in this repository

| Lesson step | What you run | Where the code is |
| --- | --- | --- |
| 0. Prepare | `./scripts/00-check-model.sh` | profile check and first Converse call |
| 1. Upload the documents | `terraform apply` | `docs/`, `terraform/s3.tf` |
| 2. Create the Knowledge Base | `terraform apply` | `terraform/opensearch.tf`, `terraform/knowledge_base.tf` |
| 3. Synchronize | `./scripts/03-sync.sh` | `start-ingestion-job`, then `get-ingestion-job` until `COMPLETE` |
| 4. Check retrieval | `./scripts/04-retrieve.sh` | two `retrieve` calls, the second filtered on `service` |
| 5. Create the guardrail | `terraform apply`, then `./scripts/05-test-guardrail.sh` | `terraform/guardrail.tf` |
| 6. Deploy the function | `terraform apply`, then `./scripts/06-invoke-function.sh` | `lambda/app.py`, `terraform/lambda.tf` |
| 7. Expose an HTTP API | `terraform apply`, then `./scripts/07-ask.sh` | `terraform/api.tf` |
| 8. Test the five behaviours | `./scripts/08-test-behaviours.sh` | |
| Cleanup | `../cleanup.sh` | `cleanup.sh` |

## Deploy

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m12-bedrock-rag-guardrails/solution     # or starter/, see below
export AWS_REGION=eu-west-3

./scripts/00-check-model.sh                  # step 0: EU model ARNs, then OK
terraform -chdir=terraform init
terraform -chdir=terraform apply             # steps 1, 2, 5, 6 and 7 (the collection takes the longest)
eval "$(./scripts/lab-env.sh)"               # BUCKET, KB_ID, DS_ID, COLL_ARN, GR_ID, API_URL...
aws s3 ls "s3://$BUCKET/docs/"               # step 1: six objects
./scripts/03-sync.sh                         # step 3: COMPLETE, 3 documents indexed
./scripts/04-retrieve.sh                     # step 4
./scripts/05-test-guardrail.sh               # step 5: GUARDRAIL_INTERVENED
./scripts/06-invoke-function.sh              # step 6: statusCode 200, "deux jours"
./scripts/07-ask.sh "Combien de jours de télétravail par semaine ?"   # step 7
./scripts/08-test-behaviours.sh              # step 8
```

`lab-env.sh` also writes the identifiers to `lab-ids.env`, so that you keep them if your terminal
closes.

To follow the lesson step by step (and with the **starter**, where you complete the
`TODO (step N)` blocks), deploy steps 1 and 2 first, then the rest:

```bash
# after TODO (step 1) and TODO (step 2)
terraform -chdir=terraform apply -target=aws_bedrockagent_data_source.docs
./scripts/03-sync.sh && ./scripts/04-retrieve.sh
# after TODO (step 5), (step 6) and (step 7)
terraform -chdir=terraform apply
```

> The API has no authentication: it is public while it exists. That is acceptable for a lab of a
> few hours on fictitious documents, never in production (JWT authorizer or IAM authentication).
> An HTTP API cuts the integration at 30 seconds: the answer is short and the effort low on purpose.

## Test

On AWS, compare each answer of `08-test-behaviours.sh` with the table of the lesson (25 euros and
`notes-de-frais.md`; `{PHONE}` and `masqué`; input block and `bloqué`; denied topic; no invented
answer). Offline, without any AWS account:

```bash
./test.sh
```

It creates `.venv`, installs the pinned versions, runs the unit tests, checks the shell scripts
(`bash -n`, ShellCheck), then runs `terraform fmt -check`, `terraform init -backend=false` and
`terraform validate` on `solution/terraform` and `starter/terraform`.

## Clean up

```bash
cd training-labs/labs/m12-bedrock-rag-guardrails
./cleanup.sh               # or ./cleanup.sh starter, add --yes to skip the confirmation
```

`terraform destroy` deletes, in dependency order, the API, the functions and their log groups, the
roles, the guardrail and its version, the data source, the Knowledge Base, the vector index, the
OpenSearch Serverless collection and its three policies, the bucket and its documents. Deleting a
Knowledge Base does not delete its collection: here the collection is a Terraform resource of its
own, so it goes too. The script then runs the checks of the lesson (collections, Knowledge Bases,
guardrails) and exits non-zero if a lab resource is still there. The next day, check in Billing that
the OpenSearch Serverless line stops growing.

## Swap the model

Bedrock is multi-model: the Converse API works with any model family enabled in your account.

```bash
aws bedrock list-inference-profiles --query 'inferenceProfileSummaries[].inferenceProfileId'
terraform -chdir=terraform apply -var model_id=<profile id> -var model_effort=""
```

The IAM policy of the function follows the profile: Terraform reads the Regions it routes to from
the profile itself. `model_effort` is an Anthropic setting passed through
`additionalModelRequestFields`; leave it empty for another family. The Knowledge Base, the
guardrail and the function code do not change. Run `00-check-model.sh` with `MODEL_ID=<profile id>`
first to check the access.

## What the offline checks cover

- The function: request validation, the exact Retrieve and Converse requests (validated against the
  botocore service models by `Stubber`), the sources, the verdicts, and that the trace values never
  leak into the response.
- The vector index builder: retries while the data access policy propagates, idempotency, error
  handling, SigV4 signing for `aoss`.
- The Terraform code: names and settings of the lesson, guardrail policies, least-privilege
  statements, pinned providers; `terraform validate` against the pinned provider schema.
- The documents and their metadata; the starter imports and its TODO markers.

What only a real deployment can show: model access in your account, the Bedrock answers and the
guardrail verdicts, the ingestion statistics, the timing of the OpenSearch Serverless data access
policy (the index builder retries for 4 minutes), and the passthrough of `output_config.effort` to
Claude Opus 5.5 through `additionalModelRequestFields`.

## Notes on the Terraform code

- Terraform creates the vector store that the console quick create would make: the collection, its encryption, network and data access policies, and the vector index
  with the field names of the quick create. Neither `hashicorp/aws` nor `awscc` can create a k-NN
  index (`awscc_opensearchserverless_collection_index` wraps the `CreateIndex` API, which builds
  automatic semantic enrichment indexes), so a small function signs the OpenSearch call and
  Terraform invokes it once (`aws_lambda_invocation`).
- The Knowledge Base role is `lab-rag-rh-kb`, created by Terraform, rather than the
  `AmazonBedrockExecutionRoleForKnowledgeBase_*` role the console would create: nothing is left to
  delete by hand.
- The function writes to its own log group only, instead of the `AWSLambdaBasicExecutionRole`
  managed policy. Every resource carries the tags `Course`, `Lab` and `ManagedBy`.
- The Terraform state stays local (`terraform/terraform.tfstate`, git-ignored).
