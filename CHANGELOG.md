# Changelog

## v1.0.1 — 2026-09-14

Per-machine configuration, found by actually installing it.

### Fixed

- **Credentials had nowhere to live.** `.mcp.json` shipped with an empty
  `GSC_CREDENTIALS_PATH` and no documented way to fill it in that survived an
  update — the only option was editing the installed plugin's config, which is
  replaced wholesale on the next version bump. The launcher now reads an
  optional `key=value` file from `~/.config/gsc-mcp/env` (override with
  `GSC_ENV_FILE`), outside the plugin directory. Values already set in the
  environment win, so anything explicit in `.mcp.json` still takes precedence.
  The file is parsed, not sourced, so a stray command in it cannot execute.
- Setup and troubleshooting docs updated to configure credentials there, with
  a log line (`[gsc-seo] loaded config from …`) to confirm it was picked up.

### Verified end to end

First real install: service account → two properties visible at `siteFullUser`
→ live search analytics returned → launcher started clean under the smoke test
with nothing preset in the environment.

## v1.0.0 — 2026-09-14

First published release. A rebuild of an unpublished internal plugin that had
been in use since March 2026, redone so it can be installed by someone other
than its author.

### What the rebuild fixed

- **The server is bundled and path-independent.** The predecessor's `.mcp.json`
  pointed at `/Users/<someone>/Documents/Claude/mcp-gsc-main/gsc_server.py`. It
  could never be installed elsewhere, and when that folder was eventually
  deleted the server stopped starting — silently, because the skills kept
  loading and the only symptom was missing tools. Everything is now
  `${CLAUDE_PLUGIN_ROOT}`-relative, and CI fails the build on any absolute path
  in the config.
- **A launcher that bootstraps its own environment.** `run-server.sh` prefers
  uv, falls back to creating a virtualenv, and fails with an actionable message
  on stderr when neither is possible. It no longer assumes the user has already
  created a venv and installed requirements.
- **Exact dependency pins.** Upstream's most recent fix exists because an
  unpinned transitive bump broke every fresh install.

### Added

- **Three skills** — `gsc-seo-analysis`, `gsc-indexing-diagnostics`,
  `gsc-site-profile`. Generalized: site-specific keyword, competitor, and page
  strategy now lives in a user-owned profile rather than baked into a SKILL.md.
- **Six commands** — `/gsc-overview`, `/keyword-report`, `/indexing-check`,
  `/sitemap-health`, `/compare-periods`, `/gsc-doctor`. The last three are new.
- **Documentation** — service-account and OAuth setup, a troubleshooting guide
  ordered by real-world frequency, a tool reference for all 21 tools, and an
  architecture note recording the design decisions.
- **Sample data** — synthetic Search Console exports with planted findings
  (striking-distance cluster, low-CTR page, cannibalization pair, brand-collision
  noise, one genuine 5xx buried in correctly-excluded pages) so the plugin can be
  demonstrated before anyone connects a property.
- **CI and evals** — structural validation, a smoke test that starts the server
  and asserts a clean MCP handshake, and twelve behavioral prompts.
- **Destructive operations off by default.** `GSC_ALLOW_DESTRUCTIVE` ships
  `false` and the skills decline to flip it on the user's behalf.

### Accuracy corrections carried into the skills

Guidance that was wrong or missing, and is now stated explicitly:

- IndexNow does not reach Google. Bing, Yandex, Seznam, and Naver participate.
- "Request indexing" is UI-only; no Google API exposes it, and the Indexing API
  is limited to job postings and livestream structured data.
- `Disallow` in robots.txt blocks crawling, not indexing — so blocking a page
  prevents Google from seeing the `noindex` that would remove it.
- "Crawled – currently not indexed" is a quality judgment; resubmission does
  nothing.
- A brand-new sitemap can report "Couldn't fetch" for hours or days while being
  entirely valid.
- The most recent 2–3 days of data are provisional and revise upward.

### Vendored

Google Search Console MCP server from
[AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc) v0.3.3, commit
`b3f2ab8` (2026-07-29), MIT licensed, unmodified. See
`plugins/gsc-seo/server/UPSTREAM.md`.

---

## Prior history (unreleased)

- **2026-05-03** — the plugin bundle was installed into Claude, where it ran
  until the referenced server directory was removed.
- **2026-03-28** — original `gsc-seo.plugin` built: one skill, three commands,
  a `.mcp.json` pointing at a local clone of mcp-gsc. Never published, never
  versioned past 0.1.0.
