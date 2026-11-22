"""Step 5: the command line, its output and one exit code per error family."""

import json
import sys

import anthropic
import pytest
from conftest import HAS_PROVIDER_SWITCH
from fake_api import VALID_SUMMARY, error_body, message_body
from strings import COST_FIRST, COST_SECOND, TRUNCATED_LINE, USAGE_FIRST, USAGE_SECOND, S, model_line

import main
import service


def run(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["main.py", *argv])
    return main.main()


def test_first_summary_writes_the_cache(workdir, fake_api, api_client, monkeypatch, capsys):
    assert run(monkeypatch, "rapport.pdf", "--profil", "direction") == 0

    out, err = capsys.readouterr()
    assert json.loads(out) == VALID_SUMMARY
    lines = err.strip().splitlines()
    assert lines[0].startswith(model_line("claude-opus-5-5", "req_011C"))
    assert lines[1] == USAGE_FIRST
    assert lines[2] == COST_FIRST


def test_second_profile_reads_the_cache_without_uploading_again(workdir, fake_api, api_client, monkeypatch, capsys):
    run(monkeypatch, "rapport.pdf", "--profil", "direction")
    capsys.readouterr()

    assert run(monkeypatch, "rapport.pdf", "--profil", "juridique") == 0

    err = capsys.readouterr().err.splitlines()
    assert err[1] == USAGE_SECOND
    assert err[2] == COST_SECOND
    assert len(fake_api.uploads) == 1


def test_default_profile_is_direction(workdir, fake_api, api_client, monkeypatch):
    run(monkeypatch, "rapport.pdf")
    assert fake_api.message_requests()[0]["messages"][0]["content"][1]["text"] == service.PROFILS["direction"]


def test_not_a_pdf_exits_2_without_any_call(workdir, fake_api, api_client, monkeypatch, capsys):
    (workdir / "notes.txt").write_text("bonjour")
    assert run(monkeypatch, "notes.txt") == 2
    assert run(monkeypatch, "absent.pdf") == 2
    assert capsys.readouterr().err.strip().splitlines() == [S["not_pdf"]] * 2
    assert fake_api.requests == []


def test_synthesis_error_exits_3(workdir, fake_api, api_client, monkeypatch, capsys):
    fake_api.queue.append((200, message_body('{"tit', stop_reason="max_tokens")))
    assert run(monkeypatch, "rapport.pdf", "--profil", "operationnel") == 3
    assert capsys.readouterr().err.strip() == TRUNCATED_LINE


def test_deleted_file_is_uploaded_again_once(workdir, fake_api, api_client, monkeypatch):
    run(monkeypatch, "rapport.pdf")
    fake_api.queue.append((404, error_body("not_found_error", "File not found")))

    assert run(monkeypatch, "rapport.pdf", "--profil", "juridique") == 0

    assert len(fake_api.uploads) == 2
    first_id, second_id = (u["id"] for u in fake_api.uploads)
    file_ids = [r["messages"][0]["content"][0]["source"]["file_id"] for r in fake_api.message_requests()]
    assert file_ids == [first_id, first_id, second_id]


@pytest.mark.parametrize(
    "status, error_type, code, message",
    [
        (401, "authentication_error", 4, S["auth"]),
        (429, "rate_limit_error", 5, S["rate"]),
        (500, "api_error", 6, S["api_error"].format(status=500)),
        (400, "invalid_request_error", 6, S["api_error"].format(status=400)),
    ],
)
def test_api_errors(workdir, fake_api, api_client, monkeypatch, capsys, status, error_type, code, message):
    fake_api.queue.append((status, error_body(error_type, "boom")))
    assert run(monkeypatch, "rapport.pdf") == code
    assert capsys.readouterr().err.startswith(message)


def test_connection_error_exits_7(workdir, monkeypatch, capsys):
    client = anthropic.Anthropic(api_key="sk-ant-test", base_url="http://127.0.0.1:9", max_retries=0)
    monkeypatch.setattr(service, "client", client)
    monkeypatch.setattr(main, "client", client)
    assert run(monkeypatch, "rapport.pdf") == 7
    assert capsys.readouterr().err.strip() == S["connection"]


@pytest.mark.skipif(not HAS_PROVIDER_SWITCH, reason="the provider switch is in solution/")
def test_unknown_provider_exits_2(workdir, fake_api, api_client, monkeypatch, capsys):
    monkeypatch.setenv("MODEL_PROVIDER", "openai")
    assert run(monkeypatch, "rapport.pdf") == 2
    assert "MODEL_PROVIDER" in capsys.readouterr().err
    assert fake_api.requests == []
