# Setup — service account (recommended)

A service account is a Google identity that belongs to a project rather than to
a person. It is the right choice for this plugin: no browser login, no token
that expires while you are mid-report, and access survives someone leaving the
company.

You need permission to create a Google Cloud project and to add users in Search
Console. If you do not have both, use [OAuth](setup-oauth.md) instead.

Roughly ten minutes, once.

## 1. Create a Google Cloud project

1. Go to <https://console.cloud.google.com/projectcreate>.
2. Name it something you will recognize in a year — `gsc-mcp`, not `My Project`.
3. Create, then make sure it is the selected project in the top bar.

## 2. Enable the Search Console API

1. Go to <https://console.cloud.google.com/apis/library/searchconsole.googleapis.com>.
2. Confirm the right project is selected.
3. **Enable**.

If you skip this, every call fails with a "has not been used in project …
before or it is disabled" error that names the project and the API. That error
message is the fix — follow its link.

## 3. Create the service account and a key

1. <https://console.cloud.google.com/iam-admin/serviceaccounts> → **Create
   service account**.
2. Name it `mcp-gsc`. No project roles are required — this account needs no
   Google Cloud permissions at all, only Search Console access, which is granted
   separately in step 4.
3. Open the account → **Keys** → **Add key** → **Create new key** → **JSON**.
4. The key downloads once. Move it somewhere stable and private:

   ```bash
   mkdir -p ~/.config/gsc-mcp
   mv ~/Downloads/<project>-<hash>.json ~/.config/gsc-mcp/credentials.json
   chmod 600 ~/.config/gsc-mcp/credentials.json
   ```

   Do not put it in a synced folder, a repo, or anywhere a backup tool will copy
   it around. This file is a credential; anyone holding it can read your Search
   Console data.

5. Note the account's email — it looks like
   `mcp-gsc@<project>.iam.gserviceaccount.com`. You need it next.

## 4. Grant it Search Console access — the step everyone misses

A valid key grants nothing on its own. Until you do this, every tool returns an
empty property list and the setup looks broken.

For **each** property you want to read:

1. <https://search.google.com/search-console> → select the property.
2. **Settings** → **Users and permissions** → **Add user**.
3. Paste the service account email.
4. Permission: **Full** if you want URL inspection (Restricted cannot inspect
   URLs), otherwise **Restricted** is enough for analytics.

Repeat per property. There is no account-wide grant.

## 5. Point the plugin at the key

Create `~/.config/gsc-mcp/env`:

```bash
cat > ~/.config/gsc-mcp/env <<'EOF'
GSC_CREDENTIALS_PATH=/Users/you/.config/gsc-mcp/credentials.json
GSC_SKIP_OAUTH=true
GSC_DATA_STATE=all
GSC_ALLOW_DESTRUCTIVE=false
EOF
chmod 600 ~/.config/gsc-mcp/env
```

Use an absolute path — `~` is not expanded inside this file.

**Configure it here, not in the plugin.** `plugins/gsc-seo/.mcp.json` ships with
an empty `GSC_CREDENTIALS_PATH` on purpose. You *can* edit the installed copy,
but plugin directories are replaced wholesale on update, so that configuration
disappears at the next version bump — and a machine-specific path has no
business in a shared repo. The launcher reads this file at startup instead, and
anything explicitly set in `.mcp.json` still takes precedence over it.

`GSC_SKIP_OAUTH=true` tells the server not to fall back to a browser login flow
when the service account is the intended path. Without it, a credentials problem
surfaces as a surprise browser window instead of a clear error.

Leave `GSC_ALLOW_DESTRUCTIVE` at `false` unless you have a specific reason — see
[destructive operations](#destructive-operations) below.

The file is parsed as `key=value`, not sourced as a shell script, so a stray
command in it cannot execute. Override its location with `GSC_ENV_FILE` if you
keep config somewhere else.

## 6. Restart and verify

Quit Claude completely (Cmd+Q — closing the window is not enough) and reopen it.
Then:

> Which Search Console properties do I have access to?

You should get the list from step 4. If it comes back empty, step 4 did not take
effect for that property — that is almost always the cause.

## Environment variables

| Variable | Required | Default | What it does |
| --- | --- | --- | --- |
| `GSC_CREDENTIALS_PATH` | Yes (service account) | — | Absolute path to the JSON key |
| `GSC_SKIP_OAUTH` | Recommended | `false` | Skip the browser OAuth fallback |
| `GSC_OAUTH_CLIENT_SECRETS_FILE` | Yes (OAuth only) | — | Path to client secrets JSON |
| `GSC_DATA_STATE` | No | `all` | `all` matches the dashboard; `final` is confirmed-only, lagging 2–3 days |
| `GSC_ALLOW_DESTRUCTIVE` | No | `false` | Enables `add_site`, `delete_site`, sitemap deletion |
| `GSC_CONFIG_DIR` | No | OS config dir | Where OAuth tokens are cached |
| `GSC_PYTHON` | No | auto | Absolute path to a Python 3.11+ interpreter, if the launcher cannot find one |
| `GSC_VENV` | No | `server/.venv` | Where the fallback virtualenv lives |
| `GSC_ENV_FILE` | No | `~/.config/gsc-mcp/env` | Where the launcher reads per-machine config from |

All of these can go in `~/.config/gsc-mcp/env`.

## Destructive operations

`add_site`, `delete_site`, and sitemap deletion are refused unless
`GSC_ALLOW_DESTRUCTIVE=true`. They change your Search Console account, and
deleting a property discards its history irreversibly.

Leave the flag off. If you genuinely need one of these, set it, do the one
operation, and set it back. Treat any suggestion to enable it permanently as a
smell.

## Rotating or revoking the key

Keys do not expire. If one is exposed, delete it in the Cloud console
(service account → Keys → delete) — that takes effect immediately — then create
a new one and update `GSC_CREDENTIALS_PATH`. Removing the service account from
Search Console's user list revokes data access separately.
