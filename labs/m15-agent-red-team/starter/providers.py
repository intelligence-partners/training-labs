"""Optional model provider switch, shared by the labs of the Intelligence Training course.

The lab code is written against the Anthropic Messages API: ``client.messages.create(...)``
and ``client.messages.stream(...)``. ``make_client()`` returns an object with that interface
for the provider selected by the ``MODEL_PROVIDER`` environment variable:

``anthropic``
    The Claude API, through ``anthropic.Anthropic()`` (reads ``ANTHROPIC_API_KEY``).
``anthropic-bedrock``
    Claude on Amazon Bedrock, through ``anthropic.AnthropicBedrock`` (the ``bedrock-runtime``
    endpoint, AWS credentials). Same request shape as the Claude API.
``bedrock``
    Any Amazon Bedrock model that supports tool use (Claude, Amazon Nova, Meta Llama,
    Mistral AI...), through the boto3 ``bedrock-runtime`` Converse API. ``ConverseClient``
    translates the Anthropic-style requests and responses, so the lab code runs unchanged.

Converse translation, in short:

- ``system``, ``messages``, ``tools`` (``strict`` included) and ``max_tokens`` are translated;
- ``cache_control`` markers (on a block, a tool, or top-level) become ``cachePoint`` blocks;
- ``output_config.format`` (structured output) becomes ``outputConfig.textFormat``;
- ``output_config.effort`` and ``thinking`` are Claude-specific and are not sent: the model's
  defaults apply;
- assistant turns returned by Converse are sent back unchanged (reasoning blocks included).

Environment variables read by the Converse translation:

``BEDROCK_CACHE_POINTS``  ``false`` to drop cache points, for a model without prompt caching.
``BEDROCK_STRICT_TOOLS``  ``false`` to drop ``strict`` on tools, for a model that rejects it.
``BEDROCK_MAX_TOKENS``    an upper bound for ``maxTokens``, for a model with a lower output limit.
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

ANTHROPIC = "anthropic"
ANTHROPIC_BEDROCK = "anthropic-bedrock"
BEDROCK = "bedrock"
PROVIDERS = (ANTHROPIC, ANTHROPIC_BEDROCK, BEDROCK)

CACHE_POINT = {"cachePoint": {"type": "default"}}


def current_provider(default: str = ANTHROPIC, allowed: tuple[str, ...] = PROVIDERS) -> str:
    """Return the provider named by MODEL_PROVIDER, or ``default`` when it is unset."""
    value = os.environ.get("MODEL_PROVIDER", "").strip().lower() or default
    if value not in allowed:
        raise SystemExit(f"MODEL_PROVIDER={value!r} is not supported by this lab. Use one of: {', '.join(allowed)}.")
    return value


def model_for(anthropic_model: str, env_vars: str | tuple[str, ...] = "BEDROCK_MODEL_ID",
              default_provider: str = ANTHROPIC) -> str:
    """Model id for the current provider.

    With the Claude API, the lesson's model id is used. On Bedrock, model ids (and inference
    profile ids) depend on your account and Region, so they are read from the environment.
    """
    if current_provider(default_provider) == ANTHROPIC:
        return anthropic_model
    names = (env_vars,) if isinstance(env_vars, str) else tuple(env_vars)
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    raise SystemExit(f"MODEL_PROVIDER={current_provider(default_provider)} needs a Bedrock model id or "
                     f"inference profile id: set {names[0]} (see .env.example).")


def aws_region(region: str | None = None) -> str | None:
    return region or os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")


def make_client(default_provider: str = ANTHROPIC, region: str | None = None,
                allowed: tuple[str, ...] = PROVIDERS):
    """Build the client for the current provider (see the module docstring)."""
    provider = current_provider(default_provider, allowed)
    if provider == ANTHROPIC:
        import anthropic

        return anthropic.Anthropic()
    if provider == ANTHROPIC_BEDROCK:
        from anthropic import AnthropicBedrock

        return AnthropicBedrock(aws_region=aws_region(region))
    import boto3

    return ConverseClient(boto3.client("bedrock-runtime", region_name=aws_region(region)))


def prices_from_env(default: dict[str, float]) -> dict[str, float]:
    """Price sheet in dollars per million tokens, optionally overridden by PRICE_SHEET (JSON).

    The defaults in the lab scripts are the lesson's prices for Claude Opus 5.5. When you run
    another model, set PRICE_SHEET to its prices, or the cost estimates (and budgets) are wrong.
    """
    raw = os.environ.get("PRICE_SHEET", "").strip()
    if not raw:
        if os.environ.get("MODEL_PROVIDER", "").strip().lower() == BEDROCK:
            print("Warning: PRICE_SHEET is not set; cost estimates use the lesson's Claude Opus 5.5 prices.",
                  file=sys.stderr)
        return dict(default)
    prices = json.loads(raw)
    missing = [key for key in default if key not in prices]
    if missing:
        raise SystemExit(f"PRICE_SHEET is missing: {', '.join(missing)} (dollars per million tokens).")
    return {key: float(prices[key]) for key in default}


# --------------------------------------------------------------------------- Converse adapter
def _flag(name: str, default: bool = True) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value not in ("0", "false", "no", "off")


@dataclass
class ConverseBlock:
    """A content block returned by Converse, exposed with the Anthropic SDK attribute names."""

    type: str  # "text", "tool_use", "thinking" (reasoning) or "other"
    raw: dict[str, Any]
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConverseUsage:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class ConverseMessage:
    content: list[ConverseBlock]
    stop_reason: str  # Converse stopReason, unchanged: end_turn, tool_use, max_tokens, ...
    usage: ConverseUsage
    model: str
    raw: dict[str, Any] = field(repr=False, default_factory=dict)


class _FinalMessageStream:
    def __init__(self, message: ConverseMessage):
        self._message = message

    def get_final_message(self) -> ConverseMessage:
        return self._message


class ConverseMessages:
    def __init__(self, runtime):
        self._runtime = runtime

    def create(self, **kwargs) -> ConverseMessage:
        request = to_converse_request(**kwargs)
        return from_converse_response(self._runtime.converse(**request), request["modelId"])

    @contextmanager
    def stream(self, **kwargs) -> Iterator[_FinalMessageStream]:
        # Converse (not ConverseStream) under the hood: the lab code only reads the final message.
        yield _FinalMessageStream(self.create(**kwargs))


class ConverseClient:
    """Minimal stand-in for ``anthropic.Anthropic`` on top of the Converse API."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.messages = ConverseMessages(runtime)


def to_converse_request(*, model: str, max_tokens: int, messages: list, system=None, tools=None,
                        output_config: dict | None = None, cache_control: dict | None = None,
                        thinking: dict | None = None) -> dict[str, Any]:
    """Translate Anthropic Messages API arguments into Converse arguments."""
    del thinking  # Claude-specific; Converse applies the model's default
    cache_points = _flag("BEDROCK_CACHE_POINTS")
    cap = os.environ.get("BEDROCK_MAX_TOKENS", "").strip()
    request: dict[str, Any] = {
        "modelId": model,
        "messages": [{"role": m["role"], "content": _content(m["content"], cache_points)} for m in messages],
        "inferenceConfig": {"maxTokens": min(max_tokens, int(cap)) if cap else max_tokens},
    }
    if cache_control and cache_points and request["messages"]:
        # Top-level cache_control caches the whole prefix: a cache point after the last block.
        request["messages"][-1]["content"].append(dict(CACHE_POINT))
    if system:
        request["system"] = _system(system, cache_points)
    if tools:
        request["toolConfig"] = {"tools": _tools(tools, cache_points)}
    fmt = (output_config or {}).get("format")
    if fmt:
        if fmt.get("type") != "json_schema":
            raise ValueError(f"Unsupported output format for Converse: {fmt.get('type')!r}")
        request["outputConfig"] = {"textFormat": {"type": "json_schema", "structure": {
            "jsonSchema": {"schema": json.dumps(fmt["schema"]), "name": fmt.get("name", "response")}}}}
    return request


def _system(system, cache_points: bool) -> list[dict]:
    if isinstance(system, str):
        return [{"text": system}]
    blocks: list[dict] = []
    for block in system:
        blocks.append({"text": block["text"]})
        if cache_points and block.get("cache_control"):
            blocks.append(dict(CACHE_POINT))
    return blocks


def _tools(tools: list[dict], cache_points: bool) -> list[dict]:
    strict = _flag("BEDROCK_STRICT_TOOLS")
    converted: list[dict] = []
    for tool in tools:
        spec: dict[str, Any] = {"name": tool["name"], "inputSchema": {"json": tool["input_schema"]}}
        if tool.get("description"):
            spec["description"] = tool["description"]
        if strict and tool.get("strict"):
            spec["strict"] = True
        converted.append({"toolSpec": spec})
        if cache_points and tool.get("cache_control"):
            converted.append(dict(CACHE_POINT))
    return converted


def _content(content, cache_points: bool) -> list[dict]:
    if isinstance(content, str):
        return [{"text": content}]
    blocks: list[dict] = []
    for item in content:
        if isinstance(item, ConverseBlock):
            blocks.append(item.raw)  # replay the model's own block unchanged
            continue
        if hasattr(item, "model_dump"):  # an Anthropic SDK block object
            item = item.model_dump(exclude_none=True)
        kind = item.get("type")
        if kind == "text":
            if not item["text"].strip():
                continue
            blocks.append({"text": item["text"]})
        elif kind == "tool_use":
            blocks.append({"toolUse": {"toolUseId": item["id"], "name": item["name"], "input": item["input"]}})
        elif kind == "tool_result":
            blocks.append({"toolResult": _tool_result(item)})
        elif kind in ("thinking", "redacted_thinking"):
            continue  # written by another provider: it cannot be replayed through Converse
        else:
            raise ValueError(f"Content block type {kind!r} is not supported by the Converse adapter")
        if cache_points and item.get("cache_control"):
            blocks.append(dict(CACHE_POINT))
    return blocks


def _tool_result(item: dict) -> dict:
    content = item.get("content", "")
    if isinstance(content, str):
        parts = [{"text": content}]
    else:
        parts = []
        for part in content:
            if part.get("type") != "text":
                raise ValueError(f"Tool result block type {part.get('type')!r} is not supported by the Converse adapter")
            parts.append({"text": part["text"]})
    result: dict[str, Any] = {"toolUseId": item["tool_use_id"], "content": parts}
    if item.get("is_error"):
        result["status"] = "error"
    return result


def from_converse_response(response: dict, model: str) -> ConverseMessage:
    """Expose a Converse response with the attributes the lab code reads on an SDK Message."""
    blocks: list[ConverseBlock] = []
    for raw in response.get("output", {}).get("message", {}).get("content", []):
        if "text" in raw:
            blocks.append(ConverseBlock(type="text", raw=raw, text=raw["text"]))
        elif "toolUse" in raw:
            use = raw["toolUse"]
            blocks.append(ConverseBlock(type="tool_use", raw=raw, id=use["toolUseId"], name=use["name"],
                                        input=use.get("input") or {}))
        elif "reasoningContent" in raw:
            blocks.append(ConverseBlock(type="thinking", raw=raw))
        else:
            blocks.append(ConverseBlock(type="other", raw=raw))
    usage = response.get("usage", {})
    return ConverseMessage(
        content=blocks,
        stop_reason=response.get("stopReason", ""),
        usage=ConverseUsage(
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            cache_creation_input_tokens=usage.get("cacheWriteInputTokens", 0),
            cache_read_input_tokens=usage.get("cacheReadInputTokens", 0),
        ),
        model=model,
        raw=response,
    )
