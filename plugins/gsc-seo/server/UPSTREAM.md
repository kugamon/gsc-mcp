# Upstream provenance

`gsc_server.py` in this directory is a **verbatim copy** of the Google Search
Console MCP server from [AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc),
MIT licensed. The upstream license is preserved here as `LICENSE.upstream`.

| | |
| --- | --- |
| Upstream repo | https://github.com/AminForou/mcp-gsc |
| Upstream package | `mcp-search-console` on PyPI |
| Vendored version | 0.3.3 |
| Vendored commit | `b3f2ab829ebc8f8294440821b4d476d75b5edadd` (2026-07-29) |
| Commit subject | `fix: pin mcp[cli]<2.0.0 to unbreak fresh installs (#41)` |
| SHA-256 (first 16) | `3777d8d5f0dbab48` |
| Local modifications | **None.** Not one line. |

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

cp /tmp/mcp-gsc/gsc_server.py  plugins/gsc-seo/server/gsc_server.py
cp /tmp/mcp-gsc/LICENSE        plugins/gsc-seo/server/LICENSE.upstream
shasum -a 256 plugins/gsc-seo/server/gsc_server.py                 # record this
```

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
