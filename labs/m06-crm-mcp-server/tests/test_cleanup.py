"""cleanup.sh removes the three Claude Code registrations of the lesson, with a stand-in `claude`."""

import os
import subprocess

from conftest import LAB

FAKE_CLAUDE = """#!/usr/bin/env bash
echo "$@" >> "$CLAUDE_CALLS"
if [ "$2" = "get" ] && [ "$3" = "orbis-ts" ]; then exit 1; fi   # pretend orbis-ts was never added
exit 0
"""


def test_cleanup_removes_registered_servers(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "claude").write_text(FAKE_CLAUDE)
    (bin_dir / "claude").chmod(0o755)
    calls = tmp_path / "calls.txt"

    result = subprocess.run(["bash", str(LAB / "cleanup.sh")], capture_output=True, text=True, timeout=60,
                            env={**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                                 "CLAUDE_CALLS": str(calls)})

    assert result.returncode == 0, result.stderr
    assert calls.read_text().splitlines() == [
        "mcp get orbis", "mcp remove orbis",
        "mcp get orbis-http", "mcp remove orbis-http",
        "mcp get orbis-ts",
    ]
    assert "unset CRM_TOKEN CRM_PUBLIC_URL" in result.stdout


def test_cleanup_without_claude_code(tmp_path):
    result = subprocess.run(["bash", str(LAB / "cleanup.sh")], capture_output=True, text=True, timeout=60,
                            env={**os.environ, "PATH": "/usr/bin:/bin"})
    assert result.returncode == 0
    assert "not found" in result.stdout
