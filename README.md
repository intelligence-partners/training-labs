<p align="left">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/ip-monogram-white.png">
    <img src="assets/ip-monogram-black.png" alt="Intelligence Partners" width="72">
  </picture>
</p>

# Intelligence Training labs

Companion code for the hands-on labs of **Intelligence Training**, the online path *Forward Deployed Engineer · AI Platform* by [Intelligence Partners](https://the-intelligence-partners.com/en/training).

Each lab follows a lesson of the course step by step. The lesson explains the why; this repository gives you the code, so you spend your time building and understanding, not retyping.

[Version française](README.fr.md)

## The labs

| Module | Lab | Folder |
| --- | --- | --- |
| M05 | A document summarization service on an LLM API | [`labs/m05-document-summary-service`](labs/m05-document-summary-service) |
| M06 | An MCP server for your CRM | [`labs/m06-crm-mcp-server`](labs/m06-crm-mcp-server) |
| M07 | A document assistant with citations (RAG) | [`labs/m07-rag-assistant-citations`](labs/m07-rag-assistant-citations) |
| M08 | An end-to-end ticket analysis agent | [`labs/m08-ticket-analysis-agent`](labs/m08-ticket-analysis-agent) |
| M10 | Your first serverless service | [`labs/m10-first-serverless-service`](labs/m10-first-serverless-service) |
| M11 | A landing zone and a golden path in Terraform | [`labs/m11-landing-zone-golden-path`](labs/m11-landing-zone-golden-path) |
| M12 | A RAG assistant on Amazon Bedrock, Knowledge Bases and Guardrails | [`labs/m12-bedrock-rag-guardrails`](labs/m12-bedrock-rag-guardrails) |
| M13 | A complete support agent on Amazon Bedrock AgentCore | [`labs/m13-agentcore-support-agent`](labs/m13-agentcore-support-agent) |
| M14 | A cost and quality dashboard for an agent | [`labs/m14-llmops-cost-quality-dashboard`](labs/m14-llmops-cost-quality-dashboard) |
| M15 | Red-teaming your own agent | [`labs/m15-agent-red-team`](labs/m15-agent-red-team) |

The workshops of M03 (prompt engineering), M16 (final project) and M17 (the IP Method) need no code: they happen in the course itself.

## How a lab is organized

```
labs/<lab>/
  README.md, README.fr.md   goal, prerequisites, cost, steps, cleanup
  starter/                  where you start, with TODO markers matching the lesson
  solution/                 the complete code, to compare or unblock yourself
  infra/                    infrastructure as code in Terraform, when the lab deploys AWS resources
  tests/                    checks that run offline, with model and AWS calls mocked
  test.sh                   installs the dependencies and runs the checks
  cleanup.sh                deletes everything the lab created, when it creates resources
  .env.example              the environment variables to set
```

## Getting started

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/<lab>
cp .env.example .env   # then fill it in
bash test.sh           # offline checks, no account needed
```

Then follow the lesson and the lab's README.

## Any model, your choice

The course is multi-model. The labs use one model provider as the worked example, as the lessons do, and most of them let you switch provider with an environment variable, for example the Anthropic API or Amazon Bedrock, which gives access to several model families through the same Converse API. Each lab's README says how.

## Costs and safety

- The AWS labs run on **your own AWS account**. Each README states the estimated cost given in the lesson. Always run the cleanup at the end.
- Model calls are billed by your provider. Set a budget alert before you start.
- Never commit your `.env` file or any credentials. The `.gitignore` excludes them.

## Checks

Every lab ships a `test.sh` that runs without any account or API key: unit tests with mocked model and AWS calls, type checks, `terraform validate` on the infrastructure. The same checks run on every push in GitHub Actions. They do not replace a real deployment, which is part of the lab.

---

The code in this repository is released under the [MIT License](LICENSE). The course itself (lessons, exercises, exams, videos) remains the property of Intelligence Partners.

Intelligence Training is published by Intelligence Partners. It is not affiliated with Amazon Web Services or with any model provider.
