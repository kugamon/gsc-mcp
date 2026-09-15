# Changelog

## v1.3.0 — 2026-09-15

Upstream shipped 0.4.0 the day after we reported three issues. Two of them are
fixed in it, one was declined with reasons, and the vendored server moves up.

### Vendored server 0.3.3 → 0.4.0

Upstream commit `f21d49c`. What it brings, all of it things this plugin reported
or relied on:

- **`sort_by` now works** (#54, ours) — the dead `orderBy` is gone and sorting
  is applied client-side.
- **`batch_url_inspection` runs concurrently** (#31) — `Semaphore(10)` +
  `to_thread` + `gather`, with a separate service instance per thread, which is
  the detail that matters since `googleapiclient` services are not thread-safe.
  10-URL batches no longer time out on `sc-domain:` properties.
- **Bare `except:` clauses narrowed** to `except Exception:` (part of #53,
  ours).
- Rich-result reporting fixes (#46, #48) and the `compare_search_periods` delta
  direction (#42), neither of which we had found.

Checked on this sync: 21 tools unchanged, no new `GSC_*` variables, dependency
ranges unchanged so the pins hold, tests 43 → 51, all passing against our copy,
launcher verified.

### The `sort_by` guidance changed shape rather than going away

The skill used to say "`sort_by` does nothing, never trust it." On 0.4.0 that is
wrong — but the trap survives in a subtler form, and getting this right matters
more than the original warning did.

**Google only ever returns rows sorted by clicks descending.** Client-side
sorting reorders the rows you received; it cannot change which rows you
received. So `sort_by=impressions` on a 200-row pull gives the
highest-impression queries *among the 200 with the most clicks* — a query with
500 impressions and zero clicks was never in that set, and no sort argument
brings it in.

Filters still do change which rows come back, so the filtered-sweep technique is
unchanged. The guidance is now version-qualified, and points at `UPSTREAM.md`
when ordering looks wrong.

### What upstream declined, and why that was worth asking

The `isError` change (#53) was declined: *"Keeping the documented string-error
convention for now."* That is the maintainer's call on his project's
conventions, and raising it as a discussion rather than a PR is how we found out
cheaply. The reasoning still stands as a rule for anything we build ourselves.

### Still open upstream

- **#52** — the event-loop fix, rebased onto 0.4.0. 0.4.0 took
  `batch_url_inspection` off the loop; the other **21** `.execute()` sites still
  block it.
- **#55** — a leftover `orderBy` in `get_search_by_page_query`, the same dead
  field removed elsewhere in 0.4.0, plus an observation that
  `check_indexing_issues` is still the sequential loop that #31 fixed next door.

## v1.2.0 — 2026-09-14

Three failure modes found by running the plugin against six months of real
data. Each one had already produced a wrong finding before it was written down.

### `sort_by` is silently ignored — the skill now says so

`get_advanced_search_analytics` accepts `sort_by` and `sort_direction` and
discards them. The server sets an `orderBy` field on the request; Google's
Search Analytics API has no such field, so it is dropped. Results always return
**clicks-descending**, whatever was asked for.

Verified twice: the [documented request body](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
has no `orderBy` member, and `sort_by=position` ascending returns positions in
the order 9.4, 18.6, 12.4, 11.0 — unchanged.

This is worse than an error, because the tool reports a sort it did not perform.
Reported upstream.

**The consequence, and the workaround.** With sorting fixed to clicks, a
200-row pull returns every query that has clicks and then fills the rest with
zero-click queries in arbitrary — in practice alphabetical — order. The most
valuable queries in an SEO analysis are exactly the high-impression zero-click
ones, so they land wherever the alphabet puts them. In real use this hid
`conga cpq alternatives` (500 impressions, position 12.5, the site's single
largest opportunity) behind a cluster of `apttus*` queries.

Filters do work. The skill now prescribes one filtered pull per commercially
meaningful term instead, and requires saying plainly that a filtered sweep is
targeted rather than exhaustive.

### The sitelink trap

A page ranking top-three with near-zero CTR reads as the most dramatic finding
on a site. Usually it is Google working correctly: sitelinks under a brand
result are each credited an impression at position ~1, while the click goes to
the main result.

The skill now requires running `get_search_by_page_query` before calling such a
page an anomaly, and documents the signature — one brand query supplying nearly
all impressions at position ~1. It also notes that sitelink impressions depress
site-wide CTR averages, so an average including them understates performance.

This one cost a real report its number-one recommendation, which was to
investigate two pages that turned out to be fine.

### Cannibalization and AI-agent queries

- **Cannibalization** now has a worked example and the paired-dimension recipe
  (`dimensions=query,page`, filtered). Query-only and page-only views both hide
  it; you have to pair them. Also notes the tell where the page holding the best
  position has the least exposure.
- **AI-agent queries** — paragraph-long persona prompts appearing as literal
  searches — are now a documented class. Report the cluster as a signal about
  comparison content; don't target the wording, which never repeats, and exclude
  them from CTR averages.

### Also

Six new evals covering each regression, and the tool table and argument
reference now carry the `sort_by` warning at the point of use.

## v1.1.0 — 2026-09-14

Designed, print-ready reports styled in the site's own brand.

### Added

- **`gsc-report` skill.** Renders a completed analysis as a self-contained HTML
  document — KPI cards, charts, tables with status pills, colour-coded callouts
  and numbered recommendations. Chat stays the default; this fires when you ask
  for "a report", "a PDF", "something I can send".
- **`assets/report-template.html`.** The document itself. Brand tokens live in a
  single `:root` block; everything else is site-agnostic.
- **Brand extraction, in `gsc-site-profile`.** Reads *computed* styles from the
  live site rather than parsing CSS, so custom properties, framework classes and
  webfonts are already resolved. Includes an area-weighted colour census that
  ranks colours by how much of the page they actually paint — which is what
  separates the two or three brand colours from the dozens a stylesheet
  declares. Cached in the profile, so it runs once per site.
- **Asset validation in CI.** The template is checked for `@page`, `@media
  print` and `page-break-inside` rules, and fails the build if it ever grows an
  external `<script src>`. Both guards are tamper-tested.

### PDF, without a PDF dependency

The template is print-optimised — A4 page box, repeating table headers, and
break guards so no card, chart or table row is ever split across a page. **Cmd-P
→ Save as PDF produces the document.** That is deliberately the whole story: no
headless Chromium, no WeasyPrint, nothing in the launcher that can break on a
customer's machine in six months.

### Charts: one path, not two

Charts are **inline SVG with a ~30-line inline script** for hover tooltips. No
charting library, no CDN.

This started as a Chart.js layer over an SVG fallback. Two things killed that:
the CDN's SRI hash could not be retrieved to verify, and a guessed integrity
hash silently blocks the script rather than failing loudly. The single-path
design turned out to be strictly better anyway — identical on screen, in print,
in an emailed file and offline; no third-party request from a document
containing a client's traffic data; and one copy of the numbers, so a chart
cannot disagree with the table beside it.

### Verified

Rendered against six months of live data with tokens extracted from
kugamon.com: Typekit webfont confirmed loaded rather than falling back, `@page`
rule parsed, 16 print rules active with break guards on cards, charts, rows and
repeating table headers, zero external scripts.

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
