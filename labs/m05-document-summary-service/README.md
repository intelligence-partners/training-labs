# Lab m05: a document summarization service

Companion code for the lab that closes module **M05, The Claude API in depth**, of the Intelligence Training course (lesson "Lab: a document summarization service"). French version: [README.fr.md](README.fr.md).

## Goal

A command-line service that takes a PDF, uploads it only once, asks Claude for a structured summary tailored to a reader profile (`direction`, `juridique`, `operationnel`), checks the response before passing it on, and prints what the call cost. A second profile on the same document rereads the PDF from the prompt cache, for a fraction of the price.

```bash
python main.py rapport.pdf --profil direction > synthese-direction.json
```

## Architecture

Four files, as in the lesson:

| File | Role |
| --- | --- |
| `schema.py` | The JSON schema sent to the API (`SCHEMA_SYNTHESE`) and the Pydantic model that revalidates the output (`Synthese`), business rules included |
| `fichiers.py` | Upload through the Files API, with a local index (`.fichiers.json`, SHA-256 of the PDF to `file_id`) so the same PDF is never sent twice |
| `service.py` | The call to Claude (`synthetiser()`), the checks and the cost (`cout_estime()`) |
| `main.py` | The command line and one exit code per error family |

`main.py` passes the PDF path to `fichiers.py`, which uploads it only if it is new; it then passes the `file_id` and the profile to `service.py`, which calls the Messages API with a frozen system prompt, the document as the cache breakpoint, structured output (`output_config.format`), `effort: "medium"` and server-side `fallbacks="default"`. The response goes through three checks before it is returned: `stop_reason` (refusal, truncation), the Pydantic schema, the business rules (three to seven key points, page numbers of at least 1).

Exit codes: `0` success, `2` not a PDF, `3` summary not reliable (refused, truncated, invalid), `4` authentication, `5` rate limit, `6` other API error, `7` connection.

## Two editions of the code

Identifiers (file, function, class and JSON field names) are the same as in both editions of the lesson. The user-facing strings follow the language of the lesson you are reading:

| Folder | Lesson | Prompts and messages |
| --- | --- | --- |
| `starter-en/`, `solution-en/` | English lesson (`content-en`) | English (`Summary failed: output truncated: ...`) |
| `starter/`, `solution/` | French lesson | French (`Synthèse impossible : sortie tronquée : ...`) |

```text
m05-document-summary-service/
├── README.md, README.fr.md
├── .env.example            variables the lab reads
├── requirements.txt        anthropic, pydantic (step 1)
├── requirements-bedrock.txt  + boto3, for the optional Bedrock path
├── requirements-dev.txt    + pytest, for the tests
├── test.sh                 offline checks (also run by CI)
├── cleanup.sh              deletes the files uploaded to the Files API
├── starter-en/ starter/    the code you start from, with TODO(step N) markers
│   └── ts/                 the TypeScript variant (step 8), with TODOs
├── solution-en/ solution/  the complete code
│   ├── schema.py fichiers.py service.py main.py
│   ├── bedrock.py          optional provider switch (not in the lesson)
│   └── ts/synthese.ts      the TypeScript variant (step 8)
└── tests/                  offline tests: every model and AWS call is mocked
```

## Prerequisites

From the lesson:

- Python 3.10 or later, a terminal, a Claude Console account and an API key in `ANTHROPIC_API_KEY` (or a profile created with `ant auth login`).
- A 10 to 40 page PDF without a password: an activity report, a standard contract, public minutes. Avoid your clients' confidential documents for an exercise.
- No AWS resources: the lab only uses the Claude API.
- Model access: `claude-opus-5-5` on the Claude API.
- Optional, step 8: Node.js 20 or later for the TypeScript variant.
- Optional, Bedrock path: an AWS account with access to a Bedrock model that supports PDF documents and structured output, and AWS credentials on your machine.

Tested with Python 3.12, Node.js 20, `anthropic` 2.12.0, `pydantic` 2.14.4, `@anthropic-ai/sdk` 1.12.0, `zod` 4.6.7, `boto3` 1.44.9 (exact pins in the requirements files and `package.json`).

## Estimated cost

As stated in the lesson: **under $1 for the whole lab** with a PDF of about twenty pages on `claude-opus-5-5`. The first summary pays for writing the document to the cache ($5 per million tokens), the following ones reread it at $0.20 per million. Files API operations are free.

The tests in this repository cost nothing: they never call a model.

## Run it

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m05-document-summary-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # or a profile created with `ant auth login`
cd starter-en                            # complete the TODOs; or cd solution-en to run the finished code
cp ~/Documents/my-report.pdf rapport.pdf # any 10 to 40 page PDF
```

Then follow the lesson's steps:

| Lesson step | Where | Command |
| --- | --- | --- |
| 1. Set up the environment | the commands above | `python -c "import anthropic, pydantic; print(anthropic.__version__, pydantic.VERSION)"` |
| 2. Write the schema | `schema.py`, `TODO(step 2)` | |
| 3. Upload only once | `fichiers.py`, `TODO(step 3)` | `python -c "import anthropic, pathlib; from fichiers import file_id_pour; print(file_id_pour(anthropic.Anthropic(), pathlib.Path('rapport.pdf')))"` |
| 4. Call the model and check the response | `service.py`, `TODO(step 4a/4b/4c)` | |
| 5. The command line and errors | `main.py`, `TODO(step 5)` | `python main.py rapport.pdf --profil direction > synthese-direction.json` |
| 6. Verify the cache | | `python main.py rapport.pdf --profil juridique > synthese-juridique.json` (within five minutes) |
| 7. Trigger the failure cases | | `SYNTHESE_MAX_TOKENS=300 python main.py rapport.pdf --profil operationnel; echo "exit code: $?"` |
| 8. (optional) TypeScript variant | `ts/synthese.ts`, `TODO(step 8)` | `cd ts && npm ci && npx tsx synthese.ts ../rapport.pdf direction` |

The usage and cost lines go to standard error; the JSON summary goes to standard output.

## Test it

```bash
bash test.sh
```

`test.sh` creates `.venv`, installs `requirements-dev.txt`, runs `npm ci` and the TypeScript type check in every `ts/` folder, compiles and imports both starters, then runs the tests against `solution/` and `solution-en/`. No API key, no AWS credentials and no network access to Claude are needed: a local fake API answers the real SDKs (Python and TypeScript) over HTTP, and botocore's `Stubber` answers Bedrock while validating every request against the service model.

What the tests cover:

- the schema and the business rules (step 2);
- the single upload and the index, including the multipart request the SDK sends (step 3);
- the exact request (model, effort, schema, cache breakpoint on the document, `fallbacks`, beta header, API version `2026-10-21`), an identical prefix across profiles, and each check: refusal with its category, truncation (`max_tokens`, `model_context_window_exceeded`), unexpected stop reason, invalid JSON and broken rules (step 4);
- every exit code and message of `main.py`, the re-upload when a `file_id` was deleted, and the cost lines of the lesson (`0.3678 $` then `0.0717 $`) (steps 5 and 6);
- the lesson's shell commands of steps 3, 5, 6 and 7, run as written in a fresh folder;
- the TypeScript variant, type-checked and run end to end against the fake API (step 8);
- `cleanup.sh`;
- the optional Bedrock path.

To check your own work while you complete the TODOs:

```bash
LAB_TARGET=starter-en .venv/bin/python -m pytest tests      # or LAB_TARGET=starter
```

## Clean up

The lab creates no AWS resource. It leaves PDFs in the Files API of your Claude workspace, listed in `.fichiers.json`; they persist until you delete them:

```bash
bash ../cleanup.sh            # from the folder where you ran main.py
```

`cleanup.sh` runs the lesson's cleanup snippet: it deletes every `file_id` of the index, then the index. The TypeScript variant uploads the PDF on every run: list your files with `client.files.list()` and delete the ones named after your PDF. If you created an API key just for this lab, revoke it in the Claude Console.

## Swap the model

- **Another Claude model**: change `MODELE` in `service.py` (and `PRIX`, so the cost line stays right). Keep `fallbacks="default"`: on a refusal, the API retries on a fallback model and the `model` line shows which one answered.
- **Amazon Bedrock (optional, not in the lesson)**: `pip install -r ../requirements-bedrock.txt`, then

  ```bash
  export MODEL_PROVIDER=bedrock
  export BEDROCK_MODEL_ID="<a model id enabled in your account>"
  export AWS_REGION=eu-west-3        # or your profile's region
  python main.py rapport.pdf --profil direction
  ```

  `bedrock.py` sends the same system prompt, profile and JSON schema through the Bedrock Runtime Converse API, with a `cachePoint` after the document, and applies the same three checks with the same exit codes. What changes: Bedrock has no Files API (the PDF bytes travel in every request, nothing to clean up), no server-side `fallbacks` (a blocked request, `content_filtered` or `guardrail_intervened`, ends with exit code 3), and the cost line is not computed because Bedrock prices depend on the model and the region. The model must support PDF documents and structured output; no model id is hard-coded.
