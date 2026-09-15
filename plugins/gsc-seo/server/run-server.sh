#!/usr/bin/env bash
#
# Launcher for the bundled Google Search Console MCP server.
#
# Why this exists: the predecessor of this plugin hardcoded an absolute path to
# a gsc_server.py sitting in someone's Documents folder. When that folder was
# deleted the server stopped starting, and the plugin's skills and commands went
# on loading as if nothing were wrong — the failure only ever surfaced as
# "tools missing". This script resolves everything relative to the plugin, so a
# fresh install works with no editing and no machine-specific paths.
#
# Resolution order:
#   1. uv  — preferred. Builds an ephemeral, correctly-pinned environment.
#   2. A virtualenv at server/.venv — created on first run if uv is absent.
#
# HARD RULE: nothing may be written to stdout. This process speaks the MCP
# stdio protocol on stdout; a single stray echo corrupts the stream and Claude
# reports the server as failed with no useful error. All diagnostics go to
# stderr, which Claude surfaces in the MCP logs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PY="$SCRIPT_DIR/gsc_server.py"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
PYTHON_VERSION="3.11"

log() { printf '[gsc-seo] %s\n' "$*" >&2; }

# ------------------------------------------------------- per-machine config --
# Credentials differ per machine and must not live in the plugin directory:
# plugin directories are replaced wholesale on update, so anything configured
# inside one is lost at the next version bump. Instead read an optional
# key=value file from the user's config directory.
#
#   ~/.config/gsc-mcp/env
#     GSC_CREDENTIALS_PATH=/Users/you/.config/gsc-mcp/credentials.json
#     GSC_SKIP_OAUTH=true
#
# Values already set in the environment win, so anything explicitly configured
# in .mcp.json still takes precedence. The file is parsed as key=value rather
# than sourced, so a stray command in it cannot execute.
CONFIG_FILE="${GSC_ENV_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/gsc-mcp/env}"
if [[ -f "$CONFIG_FILE" ]]; then
  while IFS= read -r raw || [[ -n "$raw" ]]; do
    [[ "$raw" =~ ^[[:space:]]*# ]] && continue
    [[ "$raw" =~ ^[[:space:]]*$ ]] && continue
    [[ "$raw" != *=* ]] && continue
    key="${raw%%=*}"
    value="${raw#*=}"
    key="${key//[[:space:]]/}"
    value="${value#\"}"; value="${value%\"}"
    value="${value#\'}"; value="${value%\'}"
    [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || continue
    # Only fill in what is unset or empty.
    if [[ -z "${!key:-}" ]]; then
      export "$key=$value"
    fi
  done < "$CONFIG_FILE"
  log "loaded config from $CONFIG_FILE"
fi

if [[ ! -f "$SERVER_PY" ]]; then
  log "FATAL: gsc_server.py not found at $SERVER_PY"
  log "The plugin install looks incomplete. Reinstall from https://github.com/kugamon/gsc-mcp"
  exit 1
fi

# ---------------------------------------------------------------- find uv ----
find_uv() {
  if command -v uv >/dev/null 2>&1; then command -v uv; return 0; fi
  for candidate in "$HOME/.local/bin/uv" /opt/homebrew/bin/uv /usr/local/bin/uv; do
    [[ -x "$candidate" ]] && { printf '%s' "$candidate"; return 0; }
  done
  return 1
}

# Claude launches MCP servers with a minimal PATH that often excludes the
# per-user bin directories where uv installs itself. Look there explicitly
# rather than assuming the user's interactive shell PATH.
if UV_BIN="$(find_uv)"; then
  log "starting via uv ($UV_BIN)"
  exec "$UV_BIN" run \
    --quiet \
    --no-project \
    --python "$PYTHON_VERSION" \
    --with-requirements "$REQUIREMENTS" \
    python "$SERVER_PY"
fi

# ------------------------------------------------------------ venv fallback --
VENV_DIR="${GSC_VENV:-$SCRIPT_DIR/.venv}"
VENV_PYTHON="$VENV_DIR/bin/python"

find_python() {
  if [[ -n "${GSC_PYTHON:-}" ]]; then printf '%s' "$GSC_PYTHON"; return 0; fi
  for candidate in python3.13 python3.12 python3.11 python3; do
    command -v "$candidate" >/dev/null 2>&1 && { command -v "$candidate"; return 0; }
  done
  return 1
}

if [[ ! -x "$VENV_PYTHON" ]]; then
  log "uv not found; bootstrapping a virtualenv at $VENV_DIR (first run only)"
  if ! BOOTSTRAP_PYTHON="$(find_python)"; then
    log "FATAL: no python3 on PATH and uv is not installed."
    log "Fix: install uv with  curl -LsSf https://astral.sh/uv/install.sh | sh"
    log "  or set GSC_PYTHON to a Python 3.11+ interpreter in the plugin's MCP config."
    exit 1
  fi
  # Everything below is redirected to stderr — pip is famously chatty on stdout.
  "$BOOTSTRAP_PYTHON" -m venv "$VENV_DIR" >&2
  "$VENV_PYTHON" -m pip install --quiet --upgrade pip >&2
  "$VENV_PYTHON" -m pip install --quiet -r "$REQUIREMENTS" >&2
  log "virtualenv ready"
fi

log "starting via virtualenv ($VENV_PYTHON)"
exec "$VENV_PYTHON" "$SERVER_PY"
