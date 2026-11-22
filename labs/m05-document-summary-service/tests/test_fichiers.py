"""Step 3: upload once, keyed by the SHA-256 of the PDF."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import fichiers
from fichiers import INDEX, empreinte, file_id_pour, oublier


class CountingFiles:
    def __init__(self):
        self.calls = []

    def upload(self, *, file):
        name, handle, mime = file
        self.calls.append((name, handle.read(), mime))
        return SimpleNamespace(id=f"file_011C{len(self.calls):04d}")


def test_fingerprint_is_sha256(workdir):
    pdf = Path("rapport.pdf")
    assert empreinte(pdf) == hashlib.sha256(pdf.read_bytes()).hexdigest()


def test_upload_only_once(workdir):
    client = SimpleNamespace(files=CountingFiles())
    pdf = Path("rapport.pdf")

    first = file_id_pour(client, pdf)
    second = file_id_pour(client, pdf)

    assert first == second == "file_011C0001"
    assert len(client.files.calls) == 1
    name, content, mime = client.files.calls[0]
    assert (name, mime) == ("rapport.pdf", "application/pdf")
    assert content == pdf.read_bytes()
    assert json.loads(INDEX.read_text()) == {empreinte(pdf): "file_011C0001"}


def test_forget_then_upload_again(workdir):
    client = SimpleNamespace(files=CountingFiles())
    pdf = Path("rapport.pdf")
    file_id_pour(client, pdf)

    oublier(pdf)
    assert json.loads(INDEX.read_text()) == {}
    assert file_id_pour(client, pdf) == "file_011C0002"


def test_index_is_relative_to_the_working_directory():
    assert fichiers.INDEX == Path(".fichiers.json")


def test_real_sdk_multipart_upload(workdir, fake_api, api_client):
    file_id = file_id_pour(api_client, Path("rapport.pdf"))

    assert file_id.startswith("file_011C")
    upload = fake_api.uploads[0]
    assert upload["filename"] == "rapport.pdf"
    assert upload["mime_type"] == "application/pdf"
    assert upload["request_content_type"].startswith("multipart/form-data")
    # The Files API is generally available: no beta header is needed for the upload.
    assert "files-api" not in fake_api.requests[0]["headers"].get("anthropic-beta", "")
