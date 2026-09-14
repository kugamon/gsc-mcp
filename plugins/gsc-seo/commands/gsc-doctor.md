---
description: Diagnose a broken or unauthenticated gsc-server connection, step by step
allowed-tools: ["mcp__*gsc*", "Bash", "Read"]
---

Diagnose why the Google Search Console MCP server is not working.

Work through these in order and stop at the first failure — each step assumes
the previous one passed.

**1. Is the server running at all?**
Call `get_capabilities`. Three possible outcomes:
- Returns a tool list and "Authenticated" → the server is fine; the problem is
  elsewhere. Go to step 5.
- Returns a tool list and "Not authenticated" → skip to step 4.
- The tool does not exist / no gsc tools are available → the server did not
  start. Continue to step 2.

**2. Did the launcher fail?**
The server starts via `plugins/gsc-seo/server/run-server.sh`, which writes
diagnostics to stderr. Check the MCP logs in Claude for lines prefixed
`[gsc-seo]`. The common causes, in order of frequency:
- **Neither `uv` nor a usable `python3` on the launcher's PATH.** Claude starts
  MCP servers with a minimal environment that often excludes `~/.local/bin`.
  Fix: install uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`), or set
  `GSC_PYTHON` to an absolute path to a Python 3.11+ interpreter in the plugin's
  MCP config.
- **`gsc_server.py` missing** — an incomplete install. Reinstall the plugin.
- **The venv bootstrap failed** — read the pip error in stderr.

Verify the launcher independently:
`bash plugins/gsc-seo/server/run-server.sh < /dev/null` — it should print
`[gsc-seo] starting via …` to stderr and then wait. Anything printed to
**stdout** other than MCP protocol frames is a bug; stray stdout output
corrupts the stream and makes a working server look dead.

**3. Is the plugin config pointing somewhere real?**
Read `plugins/gsc-seo/.mcp.json`. Every path must use `${CLAUDE_PLUGIN_ROOT}`.
If you find an absolute path to someone's home directory, that is the bug —
this is exactly the failure mode this plugin was rebuilt to eliminate.

**4. Authentication.**
- **Service account** — `GSC_CREDENTIALS_PATH` must point at an existing JSON
  key file. Confirm the file exists and is readable. Then confirm the service
  account's email has been added under Search Console → Settings → Users and
  permissions, for **each** property. This is the single most common setup
  failure: valid credentials, no property access. Full walkthrough in
  `docs/setup-service-account.md`.
- **OAuth** — `GSC_OAUTH_CLIENT_SECRETS_FILE` must point at a client-secrets
  JSON. Call the `reauthenticate` tool to open a browser login. Walkthrough in
  `docs/setup-oauth.md`.
- Never print the contents of a credentials file, and never paste a key into
  the conversation.

**5. Server works, but a specific call fails.**
- **"property not found"** → run `list_properties` and use the exact string.
  `sc-domain:example.com` and `https://example.com/` are different properties
  and the trailing slash matters.
- **Numbers disagree with the GSC dashboard** → check `GSC_DATA_STATE`. `final`
  lags 2–3 days; `all` matches the dashboard.
- **A destructive tool refuses to run** → that is intentional.
  `GSC_ALLOW_DESTRUCTIVE` defaults to false. Explain what enabling it allows and
  let the user decide; do not enable it on their behalf.
- **Inspection calls start failing partway through a batch** → quota, roughly
  2,000/day and 600/minute per property. Sample instead.

Report what you found, the single fix, and what the user must do themselves
(anything involving credentials, Google Cloud, or Search Console permissions).
