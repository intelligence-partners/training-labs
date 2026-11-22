"""Shared fixtures for lab m06. No model call leaves the machine; the CRM file is a temp copy.

The tests run against solution/ by default. Set LAB_TARGET=starter to check your own work.
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
LAB = TESTS.parent
TARGET = LAB / os.environ.get("LAB_TARGET", "solution")
DATA = TARGET / "crm_data.json"
TS_DIR = TARGET / "ts"
TSX = TS_DIR / "node_modules" / ".bin" / "tsx"

# Variables that could leak a credential or change the server's behaviour at import time.
SCRUBBED = ("ANTHROPIC_", "AWS_", "BEDROCK_", "MODEL_PROVIDER", "CRM_")
for _name in list(os.environ):
    if _name.startswith(SCRUBBED):
        del os.environ[_name]

sys.path.insert(0, str(TARGET))
sys.path.insert(0, str(TESTS))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def crm_file(tmp_path, monkeypatch):
    """A fresh copy of crm_data.json, used by the in-process server and by subprocesses."""
    import server

    path = tmp_path / "crm_data.json"
    shutil.copy(DATA, path)
    monkeypatch.setattr(server, "DATA_FILE", path)
    monkeypatch.setenv("CRM_DATA", str(path))
    return path


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_port(port: int, process: subprocess.Popen, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"server exited early:\n{process.stderr.read() if process.stderr else ''}")
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise TimeoutError(f"nothing listening on port {port}")


def require_node() -> None:
    if not TSX.exists():
        if os.environ.get("LAB_REQUIRE_NODE"):
            pytest.fail(f"{TS_DIR}/node_modules is missing: run npm ci there")
        pytest.skip("TypeScript dependencies not installed (npm ci in ts/)")
