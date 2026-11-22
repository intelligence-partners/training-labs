#!/usr/bin/env bash
# Cleanup for lab m06 (lesson "Nettoyage" section).
#
# Nothing was created in the cloud. Three things stay open on your machine:
# 1. the tunnel and the server: stop them with Ctrl+C in their terminals;
# 2. the servers registered in Claude Code: removed below;
# 3. the lab token: run `unset CRM_TOKEN CRM_PUBLIC_URL` in your shell
#    (a script cannot unset variables in the shell that launched it).
set -uo pipefail

if command -v claude >/dev/null 2>&1; then
  for name in orbis orbis-http orbis-ts; do
    if claude mcp get "$name" >/dev/null 2>&1; then
      claude mcp remove "$name" && echo "Removed $name from Claude Code."
    else
      echo "$name is not registered in Claude Code: nothing to remove."
    fi
  done
else
  echo "Claude Code (claude) not found: no MCP server to remove."
fi

cat <<'MSG'
Left to do by hand:
- stop cloudflared and python server.py --http (Ctrl+C); the quick tunnel URL disappears with it;
- run: unset CRM_TOKEN CRM_PUBLIC_URL in your terminal;
- remove the servers from any other MCP host where you declared them.
MSG
