"""A local stand-in for the Claude Messages API, so the lab runs end to end with no key.

Two kinds of requests reach it:
- contextualiser.py: a <document> text block then the instruction -> a one-sentence context;
- assistant.py: search_result blocks then the question -> a cited answer or the abstention.

It behaves like an ideal model, scripted: it cites only search results that were really sent,
it abstains on the two out-of-corpus questions of the lesson, and it reproduces the lesson's
example answer for the CDD question when the two expected passages are present. Tests can also
queue explicit responses (status, body).
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ABSTENTION = "Je ne trouve pas cette information dans la documentation disponible."


def error_body(error_type: str, message: str) -> dict:
    return {"type": "error", "error": {"type": error_type, "message": message}}


def message(content: list, usage: dict, stop_reason: str = "end_turn", model: str = "claude-opus-5-5") -> dict:
    return {"id": "msg_011CTEST", "type": "message", "role": "assistant", "model": model,
            "content": content, "stop_reason": stop_reason, "stop_sequence": None,
            "stop_details": None, "usage": usage}


def cite(result_index: int, result: dict) -> dict:
    return {"type": "search_result_location", "source": result["source"], "title": result["title"],
            "cited_text": result["content"][0]["text"], "search_result_index": result_index,
            "start_block_index": 0, "end_block_index": 1}


def answer(body: dict) -> dict:
    content = body["messages"][0]["content"]
    results = [b for b in content if b.get("type") == "search_result"]
    question = next(b["text"] for b in content if b.get("type") == "text")
    sources = [r["source"] for r in results]

    out_of_corpus = "salle de sport" in question or (
        "augmentations" in question and not any(s.startswith("kb://remunerations-2026.md") for s in sources))
    if out_of_corpus:
        return message([{"type": "text", "text": f"« {ABSTENTION} »"}],
                       {"input_tokens": 1190, "output_tokens": 95})

    by_source = {r["source"]: (i, r) for i, r in enumerate(results)}
    if "CDD" in question and {"kb://politique-teletravail.md#0", "kb://politique-teletravail.md#1"} <= set(by_source):
        blocks = [
            {"type": "text", "text": "Oui. En CDD de plus de six mois, le télétravail est possible avec "
                                     "l'accord écrit de votre manager",
             "citations": [cite(*by_source["kb://politique-teletravail.md#0"])]},
            {"type": "text", "text": ", jusqu'à trois jours par semaine",
             "citations": [cite(*by_source["kb://politique-teletravail.md#1"])]},
            {"type": "text", "text": "."},
        ]
        return message(blocks, {"input_tokens": 1450, "output_tokens": 210})

    first = results[0]
    blocks = [{"type": "text", "text": first["content"][0]["text"].split(".")[0],
               "citations": [cite(0, first)]}, {"type": "text", "text": "."}]
    return message(blocks, {"input_tokens": 1400, "output_tokens": 180})


def context(body: dict) -> dict:
    instruction = body["messages"][0]["content"][1]["text"]
    chunk = instruction.split("<chunk>\n", 1)[1].split("\n</chunk>", 1)[0]
    return message([{"type": "text", "text": f"Ce passage traite de : {chunk[:40]}"}],
                   {"input_tokens": 150, "output_tokens": 30, "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0}, model="claude-haiku-5-5")


class FakeAnthropicAPI:
    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.queue: list[tuple[int, dict]] = []
        self._server: ThreadingHTTPServer | None = None

    def start(self) -> "FakeAnthropicAPI":
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def do_POST(self) -> None:  # noqa: N802
                raw = self.rfile.read(int(self.headers.get("content-length") or 0))
                body = json.loads(raw)
                api.requests.append(body | {"_headers": {k.lower(): v for k, v in self.headers.items()}})
                if api.queue:
                    status, reply = api.queue.pop(0)
                elif any(b.get("type") == "search_result" for b in body["messages"][0]["content"]):
                    status, reply = 200, answer(body)
                else:
                    status, reply = 200, context(body)
                data = json.dumps(reply).encode()
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("request-id", "req_011CTEST")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        return self

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    @property
    def url(self) -> str:
        assert self._server is not None
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"
