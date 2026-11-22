"""Offline stand-in for the Claude API.

``FakeClaude`` builds a real ``anthropic.Anthropic`` client whose HTTP transport is replaced by
``httpx2.MockTransport``: the SDK still validates and serializes every request (so a wrong
parameter name fails the test), and parses scripted responses into real SDK objects.
"""
from __future__ import annotations

import itertools
import json
from typing import Any

import anthropic
import httpx2

_ids = itertools.count(1)


def text(value: str) -> dict:
    return {"type": "text", "text": value}


def tool_use(name: str, arguments: dict, block_id: str | None = None) -> dict:
    return {"type": "tool_use", "id": block_id or f"toolu_{next(_ids):04d}", "name": name, "input": arguments}


def message(content: list[dict], stop_reason: str = "end_turn", *, input_tokens: int = 1000,
            output_tokens: int = 100, cache_write: int = 0, cache_read: int = 0,
            model: str = "claude-opus-5-5") -> dict:
    return {
        "id": f"msg_{next(_ids):04d}",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": cache_write,
            "cache_read_input_tokens": cache_read,
        },
    }


def _sse(msg: dict) -> bytes:
    """Encode a message as the server-sent events of a streamed response."""
    events: list[tuple[str, dict]] = []
    start = {**msg, "content": [], "stop_reason": None,
             "usage": {**msg["usage"], "output_tokens": 0}}
    events.append(("message_start", {"type": "message_start", "message": start}))
    for index, block in enumerate(msg["content"]):
        if block["type"] == "text":
            events.append(("content_block_start", {"type": "content_block_start", "index": index,
                                                   "content_block": {"type": "text", "text": ""}}))
            events.append(("content_block_delta", {"type": "content_block_delta", "index": index,
                                                   "delta": {"type": "text_delta", "text": block["text"]}}))
        elif block["type"] == "tool_use":
            events.append(("content_block_start", {"type": "content_block_start", "index": index,
                                                   "content_block": {**block, "input": {}}}))
            events.append(("content_block_delta", {"type": "content_block_delta", "index": index,
                                                   "delta": {"type": "input_json_delta",
                                                             "partial_json": json.dumps(block["input"])}}))
        else:
            raise ValueError(block["type"])
        events.append(("content_block_stop", {"type": "content_block_stop", "index": index}))
    events.append(("message_delta", {"type": "message_delta",
                                     "delta": {"stop_reason": msg["stop_reason"], "stop_sequence": None},
                                     "usage": msg["usage"]}))
    events.append(("message_stop", {"type": "message_stop"}))
    return "".join(f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events).encode()


class FakeClaude:
    """Scripted Claude API. ``requests`` holds the JSON body of every request sent."""

    def __init__(self, responses: list[dict] | None = None):
        self.responses = list(responses or [])
        self.requests: list[dict[str, Any]] = []
        transport = httpx2.MockTransport(self._handle)
        self.client = anthropic.Anthropic(api_key="test-key", max_retries=0,
                                          http_client=httpx2.Client(transport=transport))

    def add(self, *responses: dict) -> None:
        self.responses.extend(responses)

    def _handle(self, request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        self.requests.append(body)
        if not self.responses:
            return httpx2.Response(500, json={"type": "error", "error": {"type": "api_error",
                                                                          "message": "no scripted response left"}})
        msg = self.responses.pop(0)
        if body.get("stream"):
            return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=_sse(msg))
        return httpx2.Response(200, json=msg)
