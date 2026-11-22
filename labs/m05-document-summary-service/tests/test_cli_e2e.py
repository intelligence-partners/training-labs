"""The lesson's commands, run as written, against the local fake API.

Each test copies the solution into a fresh folder next to rapport.pdf, the way the lesson
lays out its project, and runs the exact shell commands of steps 3, 5, 6 and 7, the
cleanup section and the optional TypeScript variant (step 8).
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import LAB, MINIMAL_PDF, TARGET, subprocess_env
from fake_api import VALID_SUMMARY
from strings import COST_FIRST, COST_SECOND, TRUNCATED_LINE, USAGE_FIRST, USAGE_SECOND, S, model_line

TS_DIR = TARGET / "ts"
TSX = TS_DIR / "node_modules" / ".bin" / "tsx"


@pytest.fixture
def project(tmp_path):
    for source in TARGET.glob("*.py"):
        shutil.copy(source, tmp_path / source.name)
    (tmp_path / "rapport.pdf").write_bytes(MINIMAL_PDF)
    return tmp_path


def sh(command: str, cwd: Path, fake_api, **env: str) -> subprocess.CompletedProcess:
    python_dir = str(Path(sys.executable).parent)  # the lab venv comes first, like `source .venv/bin/activate`
    full_env = subprocess_env(
        ANTHROPIC_BASE_URL=fake_api.url,
        ANTHROPIC_API_KEY="sk-ant-test",
        PATH=python_dir + os.pathsep + os.environ["PATH"],
    )
    full_env.update(env)
    return subprocess.run(["bash", "-c", command], cwd=cwd, env=full_env, capture_output=True, text=True, timeout=120)


def test_step3_upload_once(project, fake_api):
    snippet = """python -c "
import anthropic, pathlib
from fichiers import file_id_pour
print(file_id_pour(anthropic.Anthropic(), pathlib.Path('rapport.pdf')))
"
"""
    first = sh(snippet, project, fake_api)
    second = sh(snippet, project, fake_api)

    assert first.returncode == 0, first.stderr
    assert first.stdout.strip().startswith("file_011C")
    assert second.stdout == first.stdout
    assert len(fake_api.uploads) == 1


def test_steps_5_and_6_two_profiles_and_the_cache(project, fake_api):
    first = sh("python main.py rapport.pdf --profil direction > synthese-direction.json", project, fake_api)
    second = sh("python main.py rapport.pdf --profil juridique > synthese-juridique.json", project, fake_api)

    assert first.returncode == 0, first.stderr
    assert json.loads((project / "synthese-direction.json").read_text()) == VALID_SUMMARY
    assert first.stderr.splitlines()[1:] == [
        USAGE_FIRST,
        COST_FIRST,
    ]
    assert first.stderr.splitlines()[0].startswith(model_line("claude-opus-5-5", "req_011C"))
    assert second.returncode == 0, second.stderr
    assert second.stderr.splitlines()[1:] == [
        USAGE_SECOND,
        COST_SECOND,
    ]
    assert len(fake_api.uploads) == 1


def test_step7_forced_truncation(project, fake_api):
    result = sh('SYNTHESE_MAX_TOKENS=300 python main.py rapport.pdf --profil operationnel; ' + S["exit_echo"],
                project, fake_api)

    assert result.stderr.strip() == TRUNCATED_LINE
    assert result.stdout.strip() == S["exit_line"].format(code=3)
    assert fake_api.message_requests()[0]["max_tokens"] == 300


def test_step7_invalid_key_and_not_a_pdf(project, fake_api):
    invalid = sh('ANTHROPIC_API_KEY=sk-ant-invalide python main.py rapport.pdf; ' + S["exit_echo"],
                 project, fake_api)
    (project / "notes.txt").write_text("pas un PDF")
    not_pdf = sh('python main.py notes.txt; ' + S["exit_echo"], project, fake_api)

    assert invalid.stdout.strip() == S["exit_line"].format(code=4)
    assert invalid.stderr.strip() == S["auth"]
    assert not_pdf.stdout.strip() == S["exit_line"].format(code=2)
    assert len(fake_api.requests) == 1  # only the rejected call; the text file never reached the API


def test_cleanup_deletes_uploaded_files(project, fake_api):
    sh("python main.py rapport.pdf", project, fake_api)
    file_id = fake_api.uploads[0]["id"]

    result = sh(f'bash "{LAB / "cleanup.sh"}" "{project}"', project, fake_api)

    assert result.returncode == 0, result.stderr
    assert f"deleted {file_id}" in result.stdout
    assert fake_api.deleted == [file_id]
    assert not (project / ".fichiers.json").exists()


def test_cleanup_without_index(project, fake_api):
    result = sh(f'bash "{LAB / "cleanup.sh"}"', project, fake_api)
    assert result.returncode == 0
    assert "nothing to delete" in result.stdout
    assert fake_api.requests == []


def test_step8_typescript_variant(project, fake_api):
    if not TSX.exists():
        if os.environ.get("LAB_REQUIRE_NODE"):
            pytest.fail(f"{TS_DIR}/node_modules is missing: run npm ci there")
        pytest.skip("TypeScript dependencies not installed (npm ci in ts/)")

    result = subprocess.run(
        [str(TSX), "synthese.ts", str(project / "rapport.pdf"), "direction"],
        cwd=TS_DIR, capture_output=True, text=True, timeout=120,
        env=subprocess_env(ANTHROPIC_BASE_URL=fake_api.url, ANTHROPIC_API_KEY="sk-ant-test"),
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == VALID_SUMMARY
    assert result.stderr.strip() == S["ts_usage"]
    (body,) = fake_api.message_requests()
    assert body["fallbacks"] == "default"
    assert body["output_config"]["effort"] == "medium"
    assert body["messages"][0]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert fake_api.uploads[0]["filename"] == "rapport.pdf"
    assert fake_api.uploads[0]["mime_type"] == "application/pdf"
