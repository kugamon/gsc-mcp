# Upstream provenance

`gsc_server.py` in this directory is a **verbatim copy** of the Google Search
Console MCP server from [AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc),
MIT licensed. The upstream license is preserved here as `LICENSE.upstream`.

| | |
| --- | --- |
| Upstream repo | https://github.com/AminForou/mcp-gsc |
| Upstream package | `mcp-search-console` on PyPI |
| Vendored version | 0.4.2 |
| Vendored commit | `45291df024c7873b2042c83d7add70ced7bb621f` (2026-11-06) |
| Commit subject | `Release 0.4.2: fix OAuth read-only scope + token deletion (#56), offload blocking calls (#52), fix capped pagination (#62), optional null args (#58), bump mcp floor to >=1.27.2 (#40)` |
| `gsc_server.py` SHA-256 (first 16) | `ac1555717865c1c9` |
| `test_gsc_server.py` SHA-256 (first 16) | `d0c2f8ecb56c176e` |
| Local modifications | **None.** Not one line, in either file. |

### Re-sync history

| Date | From → to | Why |
| --- | --- | --- |
| 2026-11-06 | 0.4.1 → 0.4.2 | Carries our PR #52: every single-shot tool now runs its Google call in a worker thread, so concurrent tool calls stop serialising. Also fixes the OAuth scope and token-deletion bugs in #56, `has_more` / `next_start_row` above the 25,000-row cap (#62), and null-able optional args (#58). |
| 2026-09-25 | 0.4.0 → 0.4.1 | Both halves of our #55: `check_indexing_issues` now runs concurrently (the same fix #31 got for `batch_url_inspection`), and the leftover dead `orderBy` is gone from `get_search_by_page_query`. |
| 2026-09-15 | 0.3.3 → 0.4.0 | Upstream fixed three things this plugin had reported or relied on: `sort_by` now sorts client-side (#54), `batch_url_inspection` runs concurrently so 10-URL batches stop timing out (#31), and bare `except:` clauses are narrowed (#53). Also fixes rich-result reporting (#46, #48) and the `compare_search_periods` delta direction (#42). |

Checked on the 0.4.2 sync: tool count unchanged at 21, no new `GSC_*`
environment variables, test count 52 → 55. Upstream raised its `mcp[cli]` floor
to `>=1.27.2`; the exact pins here already satisfy every upstream floor, so they
are unchanged. The 10-URL cap on both batch tools is unchanged, and
`get_advanced_search_analytics` still sorts *after* the response, so the skills'
guidance — sorting reorders only the page you fetched — still holds.

One behavioural change worth knowing: upstream now requests the **read-only**
OAuth scope unless `GSC_ALLOW_DESTRUCTIVE` is true. `.mcp.json` here sets it
false, so this plugin asks for the narrower scope automatically. Upstream also
stopped deleting `token.json` when a refresh fails, which is what made a
transient network error destroy a working credential (#56).

Two files are vendored: the server and its test suite. The tests are mocked with
`unittest.mock` and need no Google credentials, so they run in CI on every push
— 55 tests covering auth, analytics, indexing, and sitemaps. Without them CI
would prove only that the server *starts*, never that a tool returns the right
thing.

## Why vendor instead of depending on the PyPI package

Both work, and the README documents `uvx mcp-search-console` as the alternative
install. Vendoring is the default here for one reason: **a pinned copy cannot
change underneath a customer.** Upstream's most recent commit exists because an
unpinned dependency broke every fresh install; a plugin that a customer installs
once and runs for a year should not inherit that risk. The cost is that upgrades
are a deliberate act, which is the trade this repo is making on purpose.

## Keeping gsc_server.py unmodified

It stays byte-identical to upstream so that re-syncing is a copy, not a merge.
Everything Kugamon adds lives *around* it — the launcher, the pinned
requirements, the skills, the commands. If a change to the server itself ever
becomes necessary, send it upstream as a PR first; carrying a local patch turns
every future sync into a conflict resolution.

## Re-syncing to a newer upstream

```bash
git clone --depth 1 https://github.com/AminForou/mcp-gsc.git /tmp/mcp-gsc
cd /tmp/mcp-gsc && git log -1 --format='%H %ad %s' --date=short   # record this

cp /tmp/mcp-gsc/gsc_server.py       plugins/gsc-seo/server/gsc_server.py
cp /tmp/mcp-gsc/test_gsc_server.py  plugins/gsc-seo/server/test_gsc_server.py
cp /tmp/mcp-gsc/LICENSE             plugins/gsc-seo/server/LICENSE.upstream
shasum -a 256 plugins/gsc-seo/server/gsc_server.py \
              plugins/gsc-seo/server/test_gsc_server.py    # record both
```

A local clone for diffing lives at `local/upstream-reference/mcp-gsc`.

Then, in order:

1. Diff upstream's `requirements.txt` / `pyproject.toml` against the pinned
   `requirements.txt` here and update the pins deliberately.
2. Re-read the tool list — `grep -c '@mcp.tool' gsc_server.py`. If the count
   changed, the skills' tool tables and `docs/tool-reference.md` are now stale.
3. Check for new `GSC_*` environment variables:
   `grep -o 'GSC_[A-Z_]*' gsc_server.py | sort -u`. New ones may need to appear
   in `.mcp.json` and the setup docs.
4. Run `scripts/smoke-test.sh` — it starts the server and asserts a clean
   MCP handshake on stdout.
5. Update this file's table, bump the plugin version, and cut a release.

## Attribution

Server by [Amin Foroutan](https://github.com/AminForou). This plugin adds the
launcher, dependency pinning, skills, commands, docs, and validation around it,
and claims no authorship of the server itself.
