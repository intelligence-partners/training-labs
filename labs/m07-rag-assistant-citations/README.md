# Lab m07: a document assistant with citations

Companion code for the lab that closes module **M07, RAG and context engineering**, of the Intelligence Training course (lesson "Lab: a document assistant with citations"). French version: [README.fr.md](README.fr.md).

## Goal

A document assistant for Brivane, a fictitious company. It ingests the internal documentation, chunks it, indexes it as vectors and as BM25, searches in hybrid mode while respecting versions and access rights, reranks the candidates, then has Claude write an answer that cites its sources, or say honestly that the documentation is silent. A small evaluation set measures retrieval and generation. Everything runs on your machine except the calls to Claude.

```bash
python assistant.py "Je suis en CDD depuis huit mois, ai-je droit au télétravail ?"
```

## Architecture

| File | Role |
| --- | --- |
| `corpus/` | Seven Markdown documents with a header (title, version, status, rights), including three deliberate traps: an archived version that contradicts the current one, a document reserved for HR, and a procedure known by its identifier (`PRC-114`) |
| `decoupage.py` | The sentence chunker with overlap from the chunking lesson |
| `ingestion.py` | Reads the corpus, splits by section then by size, writes `chunks.jsonl` |
| `contextualiser.py` | Optional: a context written by Claude Haiku 5.5 for each chunk (contextual retrieval) |
| `index.py` | Local embeddings (`intfloat/multilingual-e5-small`) and a persistent Chroma index, cosine similarity |
| `recherche.py` | Hybrid search (Chroma + BM25), status and rights filters, RRF fusion, reranking with `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` |
| `assistant.py` | Cited generation by Claude Opus 5.5 from `search_result` blocks, with a fixed abstention sentence, and formatting of the numbered sources |
| `evaluation.py` | Eleven questions: Recall@5 and MRR for retrieval (free), citation and abstention checks for generation (calls Claude) |

The archived document is indexed but filtered out by status at search time, in Chroma (`where`) and in BM25 alike; the HR document only reaches the `rh` profile. Only the original chunk text is sent to Claude, never the generated context.

The corpus is in French, and so are the prompts and outputs: both the French and the English lessons use this same code.

```text
m07-rag-assistant-citations/
├── README.md, README.fr.md
├── .env.example              variables the lab reads
├── requirements.txt          the lesson's packages (step 1), including sentence-transformers
├── requirements-bedrock.txt  + boto3, for the optional Bedrock path
├── requirements-test.txt     what the tests need (no PyTorch, no model download)
├── test.sh                   offline checks (also run by CI)
├── cleanup.sh                removes the index, chunks.jsonl and the two downloaded models
├── starter/                  corpus/ + the seven files with TODO(step N) markers
├── solution/                 corpus/ + the complete code
│   └── bedrock.py            optional provider switch (not in the lesson)
└── tests/                    offline tests (fakes/ holds a stand-in for sentence_transformers)
```

## Prerequisites

From the lesson:

- Python 3.10 or later, a terminal, about **3 GB** of disk space (libraries and two local models of about 470 MB each, downloaded from Hugging Face on first run).
- A Claude Console account and an API key in `ANTHROPIC_API_KEY`, or a profile created with `ant auth login`.
- No AWS resources: nothing billed on the cloud side.
- Model access: `claude-opus-5-5` (answers) and `claude-haiku-5-5` (optional contextualization).

Optional Bedrock path: an AWS account with access to a Bedrock model that supports search result blocks with citations (Claude models on Bedrock), and AWS credentials on your machine.

Tested with Python 3.12, `anthropic` 2.12.0, `chromadb` 1.5.9, `sentence-transformers` 6.3.0 (with `torch` 2.15.0), `rank-bm25` 0.2.2, `numpy` 2.5.5, `boto3` 1.44.9.

## Estimated cost

As stated in the lesson, at the October 27, 2026 prices: the optional contextualization of the corpus costs less than one cent with Haiku 5.5; each question to the assistant, on the order of 1 to 5 cents with Opus 5.5 depending on the length of the thinking; the generation evaluation on eleven questions, less than $0.50. Count **less than $1** for the whole lab.

The tests in this repository cost nothing: they never call a model and never download one.

## Run it

```bash
git clone https://github.com/intelligence-partners/training-labs.git
cd training-labs/labs/m07-rag-assistant-citations
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."   # or a profile created with `ant auth login`
cd starter                               # complete the TODOs; or cd solution to run the finished code
```

| Lesson step | Where | Command and expected output |
| --- | --- | --- |
| 1. Set up the environment | the commands above | `python -c "import anthropic, chromadb, sentence_transformers; print(anthropic.__version__, chromadb.__version__, sentence_transformers.__version__)"` |
| 2. Create the corpus | `corpus/` is already there, identical to the lesson's script | `ls -R corpus` |
| 3. Chunk and ingest | `decoupage.py`, `ingestion.py`, `TODO(step 3)` | `python ingestion.py` → `18 chunks écrits dans chunks.jsonl, issus de 7 fichiers` |
| 4. (optional) Contextualize the chunks | `contextualiser.py`, `TODO(step 4)` | `python contextualiser.py` |
| 5. Index | `index.py`, `TODO(step 5)` | `python index.py` → `18 vecteurs de 384 dimensions indexés dans ./index` |
| 6. Search | `recherche.py`, `TODO(step 6a/6b/6c)` | `python recherche.py "Que dit la PRC-114 avant un redémarrage ?"`, then the HR question with and without `--profil rh` |
| 7. Generate a cited answer | `assistant.py`, `TODO(step 7)` | `python assistant.py "Je suis en CDD depuis huit mois, ai-je droit au télétravail ?"` and the out-of-corpus question |
| 8. Evaluate | `evaluation.py`, `TODO(step 8)` | `python evaluation.py` (free), then `python evaluation.py --generation` |
| 9. (optional) Compare the variants | | `python evaluation.py --sans-rerank`, `--sans-hybride`, `python contextualiser.py && python index.py && python evaluation.py` |

Steps 3 to 6 and the retrieval part of step 8 were run in this repository with the real local models: `18 chunks`, `18 vecteurs de 384 dimensions`, the PRC-114 question ranks `procedure-prc-114.md#0`, `#2`, `#1` first, the employee profile never sees `remunerations-2026.md` while the `rh` profile gets it first, and the evaluation prints `Rappel@5 : 1.00   MRR : 0.93`, with the paraphrase at rank 3, exactly as in the lesson. `recherche.py` prints five lines (`k_final=5`); the lesson shows the first three.

## Test it

```bash
bash test.sh
```

`test.sh` creates `.venv`, installs `requirements-test.txt`, compiles and imports the starter, then runs the tests against `solution/`. It does not install PyTorch or download any model: `tests/fakes/sentence_transformers` is a deterministic stand-in with the same surface (tokenizer, 384-dimension embeddings, cross-encoder scores). Chroma and rank_bm25 are the real libraries. Claude is a local fake API reached by the real SDK, and Bedrock is answered by botocore's `Stubber`, which validates every request against the service model.

What the tests cover:

- the corpus and its three traps, the sentence splitter, the chunk size and overlap, the header and section parsing, and the 18 chunks with their ids and metadata (steps 2 and 3);
- the contextualization request (Haiku 5.5, thinking disabled, effort low, cached document), the rewrite of `chunks.jsonl`, the cost line, and the chunks of one document processed in a row (step 4);
- the Chroma collection: 18 vectors of 384 dimensions, cosine space, model name in the metadata, original text stored, full reindex (step 5);
- tokenization (identifiers kept, accents and stop words removed), RRF, the status and rights filters with and without hybrid search and reranking, the HR profile, the PRC-114 ranking and the exact CLI line format (step 6);
- the `search_result` blocks, the request (model, effort, `fallbacks`, beta header, abstention sentence in the system prompt, question after the results, generated context never sent), the lesson's exact cited answer and abstention, refusal and truncation messages, source numbering and cost (step 7);
- the evaluation set, the rank and scoring rules, the retrieval and generation runs (step 8), and the variants (step 9);
- the lesson's commands run as written in a fresh folder, and `cleanup.sh`;
- the optional Bedrock path.

Not covered offline: the quality of the real models (retrieval was checked once by hand, see above) and the real Claude answers, which need an API key.

To check your own work while you complete the TODOs:

```bash
LAB_TARGET=starter .venv/bin/python -m pytest tests
```

## Clean up

The lab creates no AWS resource and no recurring cost. To free the disk space:

```bash
bash ../cleanup.sh       # from the folder where you ran the lab: removes ./index, chunks.jsonl and the two models
deactivate
cd ../.. && rm -rf m07-rag-assistant-citations/.venv   # the lab's virtual environment, when you are done
```

`cleanup.sh` removes `models--intfloat--multilingual-e5-small` and `models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1` from `${HF_HOME:-~/.cache/huggingface}/hub`, as the lesson's cleanup does. If you created an API key for this lab, disable it in the Claude Console.

## Swap the model

- **Another Claude model**: change `MODELE` (and `PRIX`) in `assistant.py` for the answers, or in `contextualiser.py` for the contexts. Keep the abstention sentence verbatim in the system prompt: `evaluation.py` detects it by string comparison.
- **Other embeddings or reranker**: change `MODELE_EMBEDDINGS` (in `ingestion.py` and `index.py`) and `MODELE_RERANKER` (in `recherche.py`), then rerun `ingestion.py` and `index.py`: the model name is stored in the collection metadata so you know when a reindex is due.
- **Amazon Bedrock (optional, not in the lesson)**: `pip install -r ../requirements-bedrock.txt`, then

  ```bash
  export MODEL_PROVIDER=bedrock
  export BEDROCK_MODEL_ID="<a model id enabled in your account>"
  export BEDROCK_CONTEXT_MODEL_ID="<optional, for contextualiser.py; defaults to BEDROCK_MODEL_ID>"
  export AWS_REGION=eu-west-3
  python assistant.py "Je suis en CDD depuis huit mois, ai-je droit au télétravail ?"
  python evaluation.py --generation
  ```

  `bedrock.py` sends the same passages as Converse `searchResult` blocks with citations enabled, and the contextualization with a `cachePoint` after the document. It converts the Converse response into the shape `mettre_en_forme()`, `sources_citees()` and `evaluation.py` expect, so the output and the evaluation are unchanged. What changes: no server-side `fallbacks` on Bedrock (a blocked request, `content_filtered` or `guardrail_intervened`, prints the refusal message), search result blocks need a model that supports them, and no cost is computed because Bedrock prices depend on the model and the region. Retrieval does not change at all. No model id is hard-coded.
