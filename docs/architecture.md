# Architecture

## How it fits together

```
  Claude (Desktop / Cowork)
        │
        │  loads at startup, from the installed plugin directory
        ├─────────────── skills/     ── how to interpret GSC data
        ├─────────────── commands/   ── /gsc-overview, /keyword-report, …
        │
        │  spawns as a subprocess, stdio transport
        └──► server/run-server.sh
                  │
                  │  resolves a Python environment:
                  │    1. uv  →  ephemeral env from requirements.txt
                  │    2. venv at server/.venv (bootstrapped once)
                  │
                  └──► gsc_server.py  (vendored, unmodified, 21 MCP tools)
                            │
                            │  google-api-python-client
                            │  auth: service account key  or  OAuth token
                            ▼
                     Google Search Console API
```

Two independent halves. The skills and commands are prompt-level knowledge and
load whether or not the server works. The server is a subprocess that can fail
on its own. **A dead server therefore presents as "tools missing", never as a
broken plugin** — which is why `/gsc-doctor` exists and why the launcher logs
loudly to stderr.

## Files in this repo

| Path | What it is |
| --- | --- |
| `.claude-plugin/marketplace.json` | Marketplace manifest — what Claude reads when you add this repo as a marketplace |
| `plugins/gsc-seo/.claude-plugin/plugin.json` | Plugin manifest |
| `plugins/gsc-seo/.mcp.json` | MCP server declaration. Every path uses `${CLAUDE_PLUGIN_ROOT}` |
| `plugins/gsc-seo/server/gsc_server.py` | The MCP server. Vendored verbatim from upstream |
| `plugins/gsc-seo/server/run-server.sh` | Launcher — finds a Python environment, execs the server |
| `plugins/gsc-seo/server/requirements.txt` | Pinned dependencies |
| `plugins/gsc-seo/server/UPSTREAM.md` | Provenance and the re-sync procedure |
| `plugins/gsc-seo/skills/` | Three skills — analysis, indexing diagnostics, site profile |
| `plugins/gsc-seo/commands/` | Six slash commands |
| `plugins/gsc-seo/profiles/` | Example site profile and where to keep your real one |
| `docs/` | Setup, troubleshooting, tool reference, this file |
| `docs/modernization.md` | Review of the vendored server against the current MCP spec and SDK, with what belongs upstream vs. here |
| `sample-data/` | Synthetic GSC exports for demoing without a connected property |
| `evals/evals.json` | One behavioral prompt per skill |
| `scripts/validate_skills.py` | Structural validation, run by CI |
| `scripts/smoke-test.sh` | Starts the server and asserts a clean MCP handshake |

## Design decisions

**The server is vendored, not depended on.** Upstream publishes
`mcp-search-console` to PyPI and `uvx mcp-search-console` works — the README
documents it as the alternative. The default is a pinned local copy because a
customer who installs once should not inherit a dependency that can change
underneath them. Upstream's most recent commit exists precisely because an
unpinned transitive bump broke fresh installs.

**`gsc_server.py` is byte-identical to upstream.** Re-syncing is then a copy,
not a merge. Everything Kugamon adds lives around it. If the server itself ever
needs a change, it goes upstream as a PR — a local patch turns every future sync
into conflict resolution.

**Dependencies are pinned to exact versions.** Floating ranges are how a working
install becomes a broken one six months later, with no change on the user's side.

**Every path is `${CLAUDE_PLUGIN_ROOT}`-relative.** The plugin this replaces
hardcoded `/Users/<someone>/Documents/Claude/mcp-gsc-main/gsc_server.py`. It
could never be installed by anyone else, and when that folder was eventually
deleted the server stopped starting — silently, because skills kept loading.
That single mistake is the reason this repo exists in its current shape.

**The launcher bootstraps rather than assuming.** Requiring a user to create a
virtualenv and install requirements before the plugin works means the plugin
does not work. uv when available, a self-created venv when not, a clear stderr
error when neither is possible.

**Destructive tools stay off.** `GSC_ALLOW_DESTRUCTIVE` defaults to false in
`.mcp.json`, and the skills instruct against casually flipping it. An agent that
can delete a Search Console property on a misread instruction is not worth the
convenience.

**Site-specific strategy lives outside the plugin.** Keyword categories,
competitor lists, and page priorities go in a user-owned site profile, not in a
SKILL.md. Plugin directories are replaced on update — anything stored inside one
is lost at the next version bump — and a shared plugin should not carry one
company's competitive strategy.

## Known limits

- **16 months** of history. Search Console keeps no more; nothing here can
  recover older data.
- **Anonymized queries are omitted.** Low-volume queries are withheld for
  privacy, so the reported long tail is always incomplete and query-level
  clicks will not sum to the site total.
- **No conversion data.** GSC knows clicks, not outcomes. Joining to analytics
  is out of scope.
- **"Request indexing" cannot be automated.** It is UI-only; no Google API
  exposes it. The Indexing API is limited to job postings and livestream
  structured data.
- **IndexNow does not reach Google.** Bing, Yandex, Seznam, and Naver
  participate; Google does not.
- **URL inspection is quota limited** — roughly 2,000/day, 600/minute per
  property.
