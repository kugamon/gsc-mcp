# Troubleshooting

Ordered by how often each one actually happens. For a guided walkthrough, run
`/gsc-doctor` in Claude.

## No GSC tools available at all

The server did not start. Claude loads skills and commands from the plugin
directory independently of the MCP server, so **the plugin can look installed
and working while the server is dead** — the only symptom is that tools are
missing. This is how the predecessor of this plugin failed silently for months.

Check the MCP logs for lines prefixed `[gsc-seo]`. The launcher writes every
diagnostic to stderr.

**Neither `uv` nor `python3` found.** Claude starts MCP servers with a minimal
PATH that usually excludes `~/.local/bin`, so a uv you installed and use daily
in a terminal may be invisible here. The launcher checks `~/.local/bin`,
`/opt/homebrew/bin`, and `/usr/local/bin` explicitly, but if uv is elsewhere:

```json
"env": { "GSC_PYTHON": "/absolute/path/to/python3.11" }
```

**`gsc_server.py` not found.** Incomplete install — reinstall the plugin.

**Dependency install failed.** Read the pip output in stderr. The fallback
virtualenv lives at `plugins/gsc-seo/server/.venv`; delete it and restart to
force a clean rebuild.

**Anything on stdout kills it.** The server speaks MCP over stdout. A single
stray `echo` or a chatty pip corrupts the stream and Claude reports a failed
server with no useful error. If you modify `run-server.sh`, every diagnostic
must be redirected to stderr.

## "Skipping connection (recent failure cached)"

Claude caches a failed MCP connection for about 15 minutes rather than retrying
on every message. Fix the underlying cause, then fully quit Claude (Cmd+Q) and
reopen — a window close does not restart the MCP host, and waiting out the cache
without fixing anything just reproduces the failure.

## `list_properties` returns nothing

Authentication succeeded but the identity has access to no properties.

**Service account:** its email must be added under Search Console → Settings →
Users and permissions, for **each** property. There is no account-wide grant,
and nothing about the credentials file hints that this step is missing. This is
the most common setup failure by a wide margin.

**OAuth:** you signed in with an account that does not own the properties. Call
`reauthenticate` and pick the right account.

## "has not been used in project … or it is disabled"

The Search Console API is not enabled on the Cloud project. The error text
includes a direct link — follow it and enable. Allow a minute for it to
propagate.

## Auth errors on every call

- **OAuth, roughly weekly:** a consent screen left in Testing mode issues
  refresh tokens that expire after 7 days. Working as designed. Switch to a
  service account for anything routine.
- **Service account:** confirm `GSC_CREDENTIALS_PATH` points at a file that
  exists and is readable, and that the key has not been deleted in the Cloud
  console.
- **A browser window opens unexpectedly** on the service-account path: set
  `GSC_SKIP_OAUTH=true` so credential problems surface as errors instead of
  login prompts.

## "Property not found" for a site you can see in GSC

The `site_url` string must match exactly. `sc-domain:example.com` and
`https://example.com/` are *different properties*, and the trailing slash on a
URL-prefix property is part of the string. Always run `list_properties` and copy
the exact value rather than typing it.

## Numbers disagree with the Search Console dashboard

Check `GSC_DATA_STATE`. `all` (default) includes fresh, unconfirmed data and
matches the dashboard. `final` returns confirmed data only and lags 2–3 days.
Most "the API is wrong" reports are this.

Also: the last 2–3 days are always provisional and revise upward. A dip at the
right edge of a chart is usually not real.

## URL inspection fails partway through a batch

Quota — roughly 2,000 inspections per day and 600 per minute, per property. On a
large site, inspect priority pages plus a sample rather than everything.

Restricted-permission users cannot inspect URLs at all. If inspection fails
while analytics works, check whether the service account has **Full** rather
than **Restricted** permission on that property.

## A destructive tool refuses to run

Intentional. `add_site`, `delete_site`, and sitemap deletion require
`GSC_ALLOW_DESTRUCTIVE=true`. Deleting a property discards its history
irreversibly. Enable the flag for the one operation you need, then turn it off.

## A command or skill does not trigger

Plugins load at startup. Fully quit Claude (Cmd+Q) and reopen — closing the
window is not enough.

Installed plugins are **snapshots**. Restarting does not refetch from GitHub.
To pick up a new release: Customize → Marketplace → Sync → Update the plugin →
restart.

## Still stuck

Run `/gsc-doctor`. If the problem is in the server itself rather than this
plugin's packaging, check upstream: <https://github.com/AminForou/mcp-gsc/issues>
— note the vendored version in `plugins/gsc-seo/server/UPSTREAM.md` when
reporting.
