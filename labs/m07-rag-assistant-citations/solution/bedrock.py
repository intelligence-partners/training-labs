"""Optional provider switch (not in the lesson): the Claude calls through Amazon Bedrock.

MODEL_PROVIDER=bedrock routes assistant.repondre() and contextualiser.contextualiser()
through the Bedrock Runtime Converse API. Converse has the same building blocks as the
lesson: `searchResult` content blocks with citations for the cited answer, and a
`cachePoint` block for the cached document of the contextualisation.

The Converse response is converted into the shape of a Messages API response (text
blocks carrying `search_result_location` citations, usage, stop_reason), so
mettre_en_forme(), sources_citees() and evaluation.py run unchanged.

Differences to keep in mind:
- no server-side `fallbacks` on Bedrock: a blocked request comes back as stop_reason
  "refusal" (mapped from content_filtered / guardrail_intervened) and is not retried;
- search result blocks need a model that supports them (Claude models on Bedrock);
- the model ids come from the environment, never from this file:
  BEDROCK_MODEL_ID (answers) and BEDROCK_CONTEXT_MODEL_ID (contextualisation, defaults to
  BEDROCK_MODEL_ID); the region from the usual AWS settings (AWS_REGION or your profile);
- prices depend on the model and the region: the scripts do not compute a cost.
"""

import os
from dataclasses import dataclass, field

PROVIDERS = ("anthropic", "bedrock")

STOP_REASONS = {"content_filtered": "refusal", "guardrail_intervened": "refusal"}


def provider() -> str:
    value = os.environ.get("MODEL_PROVIDER", "anthropic").strip() or "anthropic"
    if value not in PROVIDERS:
        raise SystemExit(f"MODEL_PROVIDER doit valoir anthropic ou bedrock, pas {value!r}.")
    return value


def model_id(variable: str = "BEDROCK_MODEL_ID") -> str:
    value = os.environ.get(variable, "").strip() or os.environ.get("BEDROCK_MODEL_ID", "").strip()
    if not value:
        raise SystemExit(f"Définissez {variable} avec l'identifiant d'un modèle activé dans votre compte.")
    return value


_client = None


def client():
    global _client
    if _client is None:
        import boto3

        _client = boto3.client("bedrock-runtime")
    return _client


# -- Messages API look-alike objects --------------------------------------------------------

@dataclass
class Citation:
    source: str
    title: str
    cited_text: str = ""
    type: str = "search_result_location"


@dataclass
class TextBlock:
    text: str
    citations: list[Citation] | None = None
    type: str = "text"


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class Response:
    model: str
    stop_reason: str | None
    content: list[TextBlock] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    stop_details: None = None


def search_result_block(c: dict) -> dict:
    """The Converse equivalent of assistant.bloc_resultat(): same source, title and text."""
    return {
        "searchResult": {
            "source": f"kb://{c['id']}",
            "title": f"{c['titre']} — {c['section']}",
            "content": [{"text": c["texte"]}],  # the original text, never the generated context
            "citations": {"enabled": True},
        }
    }


def to_response(raw: dict, model: str, passages: list[dict] | None = None) -> Response:
    """Convert a Converse response into the Messages API shape used by assistant.py."""
    sent = [search_result_block(c)["searchResult"] for c in passages or []]
    blocks: list[TextBlock] = []
    for block in raw.get("output", {}).get("message", {}).get("content", []):
        if "text" in block:
            blocks.append(TextBlock(block["text"]))
        elif "citationsContent" in block:
            cited = block["citationsContent"]
            text = "".join(part.get("text", "") for part in cited.get("content", []))
            citations = []
            for c in cited.get("citations", []):
                location = c.get("location", {}).get("searchResultLocation")
                if location is None:
                    continue
                index = location.get("searchResultIndex")
                fallback = sent[index] if isinstance(index, int) and 0 <= index < len(sent) else {}
                citations.append(Citation(
                    source=c.get("source") or fallback.get("source", ""),
                    title=c.get("title") or fallback.get("title", ""),
                    cited_text="".join(s.get("text", "") for s in c.get("sourceContent", [])),
                ))
            blocks.append(TextBlock(text, citations))
        # reasoningContent and other blocks are not part of the answer
    usage = raw.get("usage", {})
    stop = raw.get("stopReason")
    return Response(
        model=model,
        stop_reason=STOP_REASONS.get(stop, stop),
        content=blocks,
        usage=Usage(
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            cache_creation_input_tokens=usage.get("cacheWriteInputTokens", 0),
            cache_read_input_tokens=usage.get("cacheReadInputTokens", 0),
        ),
    )


def repondre(question: str, passages: list[dict], systeme: str, max_tokens: int = 16000) -> Response:
    """assistant.repondre() through Converse: search results, then the question."""
    model = model_id()
    raw = client().converse(
        modelId=model,
        system=[{"text": systeme}],
        messages=[{
            "role": "user",
            "content": [search_result_block(c) for c in passages] + [{"text": question}],
        }],
        inferenceConfig={"maxTokens": max_tokens},
    )
    return to_response(raw, model, passages)


def contextualiser(document: str, consigne: str, max_tokens: int = 300) -> tuple[str, Usage]:
    """contextualiser.contextualiser() through Converse: cached document, then the instruction."""
    model = model_id("BEDROCK_CONTEXT_MODEL_ID")
    raw = client().converse(
        modelId=model,
        messages=[{
            "role": "user",
            "content": [
                {"text": f"<document>\n{document}\n</document>"},
                {"cachePoint": {"type": "default"}},
                {"text": consigne},
            ],
        }],
        inferenceConfig={"maxTokens": max_tokens},
    )
    reponse = to_response(raw, model)
    if reponse.stop_reason != "end_turn":
        return "", reponse.usage
    return "".join(b.text for b in reponse.content).strip(), reponse.usage
