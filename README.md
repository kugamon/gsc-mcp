# gsc-mcp

[![validate](https://github.com/kugamon/gsc-mcp/actions/workflows/validate.yml/badge.svg)](https://github.com/kugamon/gsc-mcp/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A Claude Desktop / Cowork **plugin marketplace** that ships a single plugin
(`gsc-seo`) for working with Google Search Console: three skills, six slash
commands, and a **bundled MCP server** exposing 21 GSC tools.

**This repo does install an MCP server** — that is the point of it. The server
is a pinned, unmodified copy of [AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc),
launched from inside the plugin with no machine-specific paths, so installing
the plugin is the whole setup apart from Google credentials.

**What it does not do:** it cannot grant you Search Console access you do not
already have, it cannot request indexing for a URL (that is UI-only, no API
exposes it), it cannot submit to Google via IndexNow (Google does not
participate), and it cannot see more than 16 months of history. The skills say
so rather than inventing a workaround.

> **Private repo.** Adding a private repo as a marketplace requires your Claude
> GitHub authorization to have access to it. See
> [Install](#install) for the local-folder route, which needs no GitHub access
> at all.

## Why this plugin

Claude does not know, out of the box:

- That `sc-domain:example.com` and `https://example.com/` are different
  properties, and that guessing one produces a confusing empty result.
- That "Crawled – currently not indexed" is a quality judgment, not a technical
  fault — so resubmitting, rebuilding the sitemap, and requesting indexing all
  do nothing.
- That a sitemap "Couldn't fetch" error usually means a redirect or content-type
  problem, and that a brand-new sitemap shows it for hours while being perfectly
  valid.
- That `Disallow` in robots.txt blocks crawling, not indexing — so blocking a
  page you want removed prevents Google from ever seeing the `noindex` that
  would remove it.
- That IndexNow does not reach Google, however many blog posts imply otherwise.
- That branded queries have to be split out before any CTR average means
  anything.
- That the last two to three days of data are provisional and always revise up.

Each of those is a confident wrong answer waiting to happen. The skills here
encode the correct one, along with the analysis workflows — striking-distance
keywords, cannibalization, drop diagnosis — that turn Search Console data into
decisions.

## What problems do these skills solve?

| Pain | Skill / command | What it does |
| --- | --- | --- |
| "Give me an SEO report" produces a wall of undifferentiated numbers | `gsc-seo-analysis` · `/gsc-overview` | Splits branded from non-branded, applies CTR benchmarks by position, ends with recommendations that name specific pages |
| "What should I work on next?" | `/keyword-report` | Sorts every query into winners, striking distance, low-CTR, off-page-one, long tail — and finds which page actually ranks |
| Traffic dropped and nobody knows why | `/compare-periods` | Classifies the drop into one of four shapes before proposing a cause, instead of blaming an algorithm update |
| Pages are not indexed and the Search Console messages are cryptic | `gsc-indexing-diagnostics` · `/indexing-check` | Decodes each status, separates broken from working-as-intended from judgment calls |
| "Couldn't fetch" on a sitemap | `/sitemap-health` | Walks the actual causes in order — redirects, content type, robots.txt, CDN — and says so when the config is fine and the status is just stale |
| Reports are generic because Claude does not know the business | `gsc-site-profile` | Builds a site profile from existing GSC data, stored outside the plugin so updates do not erase it |
| The server silently stopped working and the plugin still looked installed | `/gsc-doctor` | Walks launcher, config, auth, and per-call failures in dependency order |
| An agent with delete access to your Search Console account | Built in | `GSC_ALLOW_DESTRUCTIVE` ships `false`; the skills refuse to flip it for you |

## Prerequisites

1. **Claude Desktop or Cowork** with plugin support.
2. **Google Search Console access** to at least one verified property.
3. **Google credentials** — either a service account (recommended) or OAuth:
   - [docs/setup-service-account.md](docs/setup-service-account.md) — no browser
     login, no expiring tokens, survives staff changes. ~10 minutes.
   - [docs/setup-oauth.md](docs/setup-oauth.md) — no Google Cloud service account
     needed, but tokens expire weekly in Testing mode.
4. **`uv` or Python 3.11+.** The launcher prefers
   [uv](https://docs.astral.sh/uv/) and falls back to building a virtualenv. If
   neither exists it tells you exactly what to install, on stderr.

## Skills

| Skill | Triggers on | Covers |
| --- | --- | --- |
| `gsc-seo-analysis` | "analyze SEO performance", "check search console", "keyword rankings", "why did traffic drop" | Metric interpretation, branded/non-branded, CTR benchmarks, five analysis workflows, report structure |
| `gsc-indexing-diagnostics` | "not indexed", "Couldn't fetch", "blocked by robots.txt", "audit indexing" | Status-by-status decoding, the robots.txt trap, crawl acceleration ranked by what works, migration checklist |
| `gsc-site-profile` | "set up my site profile", "the reports are too generic" | Building the profile that makes reports business-specific, and where to keep it |

## Commands

| Command | Does |
| --- | --- |
| `/gsc-overview` | Performance, top queries, top pages, sitemap health, quick wins |
| `/keyword-report` | Opportunity buckets with the ranking page for each |
| `/indexing-check` | Indexing audit split into broken / intended / judgment calls |
| `/sitemap-health` | Sitemap fetch status and "Couldn't fetch" diagnosis |
| `/compare-periods` | Period comparison with a diagnosis, not just deltas |
| `/gsc-doctor` | Step-by-step repair of a broken server or auth setup |

## MCP tools

21 tools across orientation, search analytics, URL inspection, and sitemaps —
full list with arguments and quotas in
[docs/tool-reference.md](docs/tool-reference.md).

Three are destructive (`add_site`, `delete_site`, sitemap deletion) and refuse
to run unless `GSC_ALLOW_DESTRUCTIVE=true`. That default is deliberate: deleting
a property discards its history irreversibly.

## Repo layout

```
gsc-mcp/
├── .claude-plugin/marketplace.json   # marketplace manifest
├── .github/workflows/validate.yml    # structure checks + server smoke test
├── docs/                             # setup, troubleshooting, tools, architecture
├── evals/evals.json                  # one behavioral prompt per skill
├── sample-data/                      # synthetic GSC exports — demo with no credentials
├── scripts/
│   ├── validate_skills.py            # run by CI; catches absolute paths, version drift
│   └── smoke-test.sh                 # starts the server, asserts a clean MCP handshake
└── plugins/
    └── gsc-seo/                      # ← the installable plugin
        ├── .claude-plugin/plugin.json
        ├── .mcp.json                 # all paths ${CLAUDE_PLUGIN_ROOT}-relative
        ├── server/                   # vendored MCP server + launcher + pins
        ├── skills/                   # 3 skills
        ├── commands/                 # 6 slash commands
        └── profiles/                 # example site profile
```

The repo root is a marketplace even though it ships one plugin: another plugin
can be added under `plugins/` later and the install URL never changes.

## Install

### Option 1 — Add marketplace (recommended)

Customize → Marketplace → **+ Add marketplace** → enter `kugamon/gsc-mcp` →
**Sync** → **Install** `gsc-seo` → quit Claude completely (Cmd+Q) and reopen.

While this repo is private, your Claude GitHub authorization must have access
to it. If sync fails with "not a marketplace", that is usually the cause.

### Option 2 — Local folder

Clone the repo, then Customize → Marketplace → add a local folder and pick
`plugins/gsc-seo/` — the directory containing `.claude-plugin/plugin.json`.
Needs no GitHub authorization.

### Option 3 — settings.json

```json
{
  "extraKnownMarketplaces": {
    "gsc-seo-marketplace": {
      "source": { "source": "github", "repo": "kugamon/gsc-mcp" }
    }
  },
  "enabledPlugins": { "gsc-seo@gsc-seo-marketplace": true }
}
```

### Then: credentials

Follow [docs/setup-service-account.md](docs/setup-service-account.md). The one
step people miss is granting the service account access **inside Search Console**
— a valid key with no property grant returns an empty list and looks broken.

### Alternative: skip the bundled server

If you would rather track upstream directly than use the pinned copy, point the
MCP config at the published package instead:

```json
{ "command": "uvx", "args": ["mcp-search-console"] }
```

The skills and commands work identically. You trade pinning for automatic
upstream updates — see
[plugins/gsc-seo/server/UPSTREAM.md](plugins/gsc-seo/server/UPSTREAM.md) for why
this repo defaults the other way.

## Verify

After restarting Claude:

> Which Search Console properties do I have access to, and how did my top
> non-branded keywords do over the last 28 days?

You should see the property list, then a report that separates branded from
non-branded traffic and names specific queries. If no GSC tools appear at all,
run `/gsc-doctor` — and note that the skills load whether or not the server
started, so "tools missing" is the only symptom a dead server produces.

## Sample prompts

- "Run a full SEO overview for my site."
- "Which keywords are we closest to getting onto page one for?"
- "Search traffic dropped 30% this month — what happened?"
- "Search Console says 'Couldn't fetch' for my sitemap. Is it actually broken?"
- "Audit indexing on my top 50 pages and tell me what's genuinely wrong."
- "Are any two of my pages competing for the same keyword?"
- "Show me what a keyword report looks like — I haven't connected GSC yet."
  (uses `sample-data/`)
- "Set up a site profile so these reports stop being generic."

## Troubleshooting

**Marketplace sync says "not a marketplace" or "no manifest".** Either the
branch has no `.claude-plugin/marketplace.json` at its root, or — while this
repo is private — your Claude GitHub authorization cannot see it.

**Plugin installs but no GSC tools appear.** The server did not start. Skills
and commands load independently of it, so the plugin looks fine. Check the MCP
logs for `[gsc-seo]` lines and run `/gsc-doctor`.

**"Skipping connection (recent failure cached)".** Claude caches a failed MCP
connection for ~15 minutes. Fix the cause, then fully quit (Cmd+Q) and reopen —
closing the window does not restart the MCP host.

**A skill or command does not trigger.** Plugins load at startup; a full restart
is required. Installed plugins are snapshots — picking up a new release means
Sync → Update → restart, not just restart.

**`list_properties` is empty.** Authentication worked; the identity has access
to nothing. Add the service account email under Search Console → Settings →
Users and permissions, per property.

Everything else: [docs/troubleshooting.md](docs/troubleshooting.md).

## Contributing

PRs welcome for analysis workflows, additional GSC failure modes, and
corrections where a skill states something that is no longer true — Google
changes these behaviors and stale guidance is worse than none.

Two rules:

- **Keep skills terse.** They are prompts, not documentation. If it does not
  change what Claude does, it belongs in `docs/`.
- **Do not modify `plugins/gsc-seo/server/gsc_server.py`.** It is a verbatim
  upstream copy and CI checks its hash. Server changes go to
  [upstream](https://github.com/AminForou/mcp-gsc) as a PR.

Run `python3 scripts/validate_skills.py` and `./scripts/smoke-test.sh` before
opening a PR; CI runs both.

## Related projects

- [salesforce-core-skills](https://github.com/kugamon/salesforce-core-skills) —
  fifteen Salesforce skills for AI agents
- [salesforce-isv-skills](https://github.com/kugamon/salesforce-isv-skills) —
  skills for Salesforce ISVs and consulting partners
- [salesforce-mcp-auto-auth-chrome](https://github.com/kugamon/salesforce-mcp-auto-auth-chrome) —
  Salesforce MCP server with automatic session refresh from Chrome
- [perplexity-plugin](https://github.com/kugamon/perplexity-plugin) — Perplexity
  MCP servers as a Claude plugin
- [reddit-mcp-chrome](https://github.com/kugamon/reddit-mcp-chrome) ·
  [linkedin-mcp-chrome](https://github.com/kugamon/linkedin-mcp-chrome) — MCP
  servers using your Chrome session

## License

MIT — see [LICENSE](LICENSE).

`plugins/gsc-seo/server/gsc_server.py` is an unmodified copy of
[mcp-gsc](https://github.com/AminForou/mcp-gsc), Copyright (c) 2025 Amin
Foroutan, redistributed under the MIT License. The upstream license is preserved
at `plugins/gsc-seo/server/LICENSE.upstream` and provenance is recorded in
`plugins/gsc-seo/server/UPSTREAM.md`.

Not affiliated with Google or with Anthropic. "Google Search Console" is a
trademark of Google LLC.
