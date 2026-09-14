#!/usr/bin/env bash
#
# Smoke test: start the bundled server and assert a clean MCP handshake.
#
# This catches the failure that structural validation cannot — a server that is
# correctly packaged but does not actually start, because a dependency is
# unresolvable, the launcher cannot find a Python, or something writes to
# stdout and corrupts the protocol stream.
#
# It does NOT need Google credentials. The MCP initialize handshake happens
# before any call to the Search Console API.
#
#   ./scripts/smoke-test.sh

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCHER="$REPO_ROOT/plugins/gsc-seo/server/run-server.sh"
TIMEOUT_SECONDS=180

if [[ ! -f "$LAUNCHER" ]]; then
  echo "FAIL: launcher not found at $LAUNCHER"
  exit 1
fi

echo "Starting server via $LAUNCHER"
echo "(first run may take a while — it resolves or builds a Python environment)"

STDOUT_FILE="$(mktemp)"
STDERR_FILE="$(mktemp)"
trap 'rm -f "$STDOUT_FILE" "$STDERR_FILE"' EXIT

# A minimal MCP initialize request. A conforming server answers with a JSON-RPC
# result carrying protocolVersion, then exits when stdin closes.
REQUEST='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke-test","version":"1.0.0"}}}'

# CLAUDE_PLUGIN_ROOT is normally set by Claude; set it so the launcher behaves
# exactly as it will in production.
export CLAUDE_PLUGIN_ROOT="$REPO_ROOT/plugins/gsc-seo"

# Run the launcher in the FOREGROUND, reading the piped stdin.
#
# Do not be tempted to background it with `&` and wait on the PID: a job
# started in the background by a non-interactive shell has its stdin
# redirected from /dev/null, so the server receives no request, answers
# nothing, and a perfectly healthy server fails this test. That mistake cost
# an hour the first time.
#
# No watchdog is needed in the common case — the server exits cleanly when
# stdin closes. `timeout` is used when available (GNU coreutils, or gtimeout
# from Homebrew) purely to bound a genuine hang.
run_launcher() {
  if command -v timeout >/dev/null 2>&1; then
    timeout "$TIMEOUT_SECONDS" bash "$LAUNCHER"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$TIMEOUT_SECONDS" bash "$LAUNCHER"
  else
    bash "$LAUNCHER"
  fi
}

# Hold stdin open well past the handshake. On a cold first run the launcher
# spends most of this window resolving a Python environment and has not started
# reading stdin yet — close it too early and the server exits before it ever
# answers, which looks identical to a broken server.
{
  printf '%s\n' "$REQUEST"
  sleep 30
} | run_launcher >"$STDOUT_FILE" 2>"$STDERR_FILE"

echo
echo "--- stderr (diagnostics) ---"
sed 's/^/  /' "$STDERR_FILE" | head -30

FAILED=0

if grep -q '"protocolVersion"' "$STDOUT_FILE"; then
  echo
  echo "PASS: server responded to initialize with a protocol version"
else
  echo
  echo "FAIL: no MCP initialize response on stdout"
  echo "--- stdout ---"
  sed 's/^/  /' "$STDOUT_FILE" | head -20
  FAILED=1
fi

# Every stdout line must be a JSON-RPC frame. Anything else means something
# printed to stdout, which breaks the transport in ways that are miserable to
# debug from Claude's side.
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  if [[ "$line" != \{* ]]; then
    echo "FAIL: non-JSON output on stdout, which corrupts the MCP stream:"
    echo "  $line"
    FAILED=1
  fi
done < "$STDOUT_FILE"

if [[ $FAILED -eq 0 ]]; then
  echo "PASS: stdout carried only JSON-RPC frames"
  echo
  echo "Smoke test passed. The server starts and speaks MCP."
  echo "It says nothing about credentials — run /gsc-doctor in Claude for that."
fi

exit $FAILED
