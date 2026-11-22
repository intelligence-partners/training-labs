"""A local stand-in for the Claude API, so the lab runs end to end with no key and no network.

It implements just what the lab calls:
- POST /v1/files            -> FileMetadata (counts uploads)
- DELETE /v1/files/{id}     -> deletion marker
- POST /v1/messages         -> a summary, with the prompt cache emulated per file_id

The real SDKs (Python and TypeScript) talk to it over HTTP through ANTHROPIC_BASE_URL or
base_url, so the request they build is the one the real API would receive. Tests can
queue explicit responses (status, body) to simulate refusals and API errors.
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count

CACHED_PREFIX_TOKENS = 61840
INPUT_TOKENS = {"direction": 72, "juridique": 74, "operationnel": 70}

VALID_SUMMARY = {
    "titre": "Rapport d'activité 2025",
    "type_document": "rapport",
    "resume": "Le chiffre d'affaires progresse. La marge recule. Deux décisions sont attendues.",
    "points_cles": ["Croissance de 12 %", "Marge en recul", "Plan d'investissement 2026"],
    "chiffres_cles": [{"libelle": "Chiffre d'affaires", "valeur": "48,2 M€", "page": 4}],
    "risques": ["Dépendance à un client majeur."],
    "questions_ouvertes": ["Le calendrier du plan n'est pas précisé."],
}


def error_body(error_type: str, message: str) -> dict:
    return {"type": "error", "error": {"type": error_type, "message": message}}


def message_body(text: str, stop_reason: str = "end_turn", usage: dict | None = None,
                 stop_details: dict | None = None, model: str = "claude-opus-5-5") -> dict:
    return {
        "id": "msg_011CTEST",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "stop_details": stop_details,
        "usage": usage or {"input_tokens": 10, "output_tokens": 20},
    }


class FakeAnthropicAPI:
    def __init__(self) -> None:
        self.requests: list[dict] = []  # {"method", "path", "headers", "body"}
        self.queue: list[tuple[int, dict]] = []  # explicit responses for /v1/messages
        self.uploads: list[dict] = []
        self.deleted: list[str] = []
        self._cache: set[str] = set()
        self._ids = count(1)
        self._server: ThreadingHTTPServer | None = None

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> "FakeAnthropicAPI":
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:  # keep test output quiet
                pass

            def _send(self, status: int, body: dict) -> None:
                data = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("request-id", f"req_011CTEST{next(api._ids):04d}")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _record(self) -> tuple[str, bytes]:
                length = int(self.headers.get("content-length") or 0)
                raw = self.rfile.read(length) if length else b""
                path = self.path.split("?")[0]
                api.requests.append({
                    "method": self.command,
                    "path": path,
                    "query": self.path.partition("?")[2],
                    "headers": {k.lower(): v for k, v in self.headers.items()},
                    "body": raw,
                })
                return path, raw

            def do_POST(self) -> None:  # noqa: N802 (http.server naming)
                path, raw = self._record()
                bearer = (self.headers.get("authorization") or "").removeprefix("Bearer ")
                if "sk-ant-invalide" in (self.headers.get("x-api-key"), bearer):
                    return self._send(401, error_body("authentication_error", "invalid x-api-key"))
                if path == "/v1/files":
                    return self._send(200, api._upload(raw, self.headers.get("content-type", "")))
                if path == "/v1/messages":
                    if api.queue:
                        return self._send(*api.queue.pop(0))
                    return self._send(200, api._summarize(json.loads(raw)))
                return self._send(404, error_body("not_found_error", f"unknown path {path}"))

            def do_DELETE(self) -> None:  # noqa: N802
                path, _ = self._record()
                file_id = path.rsplit("/", 1)[-1]
                api.deleted.append(file_id)
                return self._send(200, {"id": file_id, "type": "file_deleted"})

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

    # -- helpers for assertions -------------------------------------------
    def message_requests(self) -> list[dict]:
        return [json.loads(r["body"]) | {"_headers": r["headers"], "_query": r["query"]}
                for r in self.requests if r["path"] == "/v1/messages"]

    # -- behaviour ---------------------------------------------------------
    def _upload(self, raw: bytes, content_type: str) -> dict:
        match = re.search(rb'filename="([^"]*)"', raw)
        filename = match.group(1).decode() if match else "unnamed"
        part_type = re.search(rb"Content-Type: ([^\r\n]+)", raw, re.I)
        file_id = f"file_011CTEST{next(self._ids):04d}"
        self.uploads.append({"id": file_id, "filename": filename,
                             "mime_type": part_type.group(1).decode() if part_type else None,
                             "request_content_type": content_type})
        return {
            "id": file_id,
            "type": "file",
            "filename": filename,
            "mime_type": "application/pdf",
            "size_bytes": len(raw),
            "created_at": "2026-11-21T10:00:00Z",
            "downloadable": False,
        }

    def _summarize(self, body: dict) -> dict:
        content = body["messages"][0]["content"]
        file_id = next(b["source"]["file_id"] for b in content if b.get("type") == "document")
        profile_text = next((b["text"] for b in content if b.get("type") == "text"), "")
        if "juridique" in profile_text or "legal" in profile_text:  # French or English edition
            profile = "juridique"
        elif "opérationnel" in profile_text or "operations" in profile_text:
            profile = "operationnel"
        else:
            profile = "direction"
        if body.get("max_tokens", 0) <= 300:
            return message_body('{"titre": "Rapport d\'act', stop_reason="max_tokens",
                                usage={"input_tokens": 70, "output_tokens": body["max_tokens"]})
        warm = file_id in self._cache
        self._cache.add(file_id)
        usage = {
            "input_tokens": INPUT_TOKENS[profile],
            "cache_creation_input_tokens": 0 if warm else CACHED_PREFIX_TOKENS,
            "cache_read_input_tokens": CACHED_PREFIX_TOKENS if warm else 0,
            "output_tokens": 2950 if warm else 2914,
        }
        return message_body(json.dumps(VALID_SUMMARY, ensure_ascii=False), usage=usage)
