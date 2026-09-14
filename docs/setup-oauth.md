# Setup — OAuth (alternative)

Use OAuth when you cannot create a Google Cloud service account, or when you
want the plugin to act as *you* rather than as a separate identity.

The trade: no Search Console permission step (you already have access to your
own properties), but tokens expire and you will occasionally have to
re-authenticate through a browser. For unattended or scheduled use, prefer
[the service account path](setup-service-account.md).

## 1. Project and API

Same as the service-account setup:

1. Create or pick a project at <https://console.cloud.google.com>.
2. Enable the Search Console API:
   <https://console.cloud.google.com/apis/library/searchconsole.googleapis.com>.

## 2. Configure the consent screen

<https://console.cloud.google.com/apis/credentials/consent>

1. User type **External** unless you are on Workspace and every user is
   internal — External is fine for a personal tool.
2. Fill in app name and your email.
3. Scopes: add `https://www.googleapis.com/auth/webmasters`. This is the only
   scope the server requests.
4. Under **Test users**, add the Google account that owns the Search Console
   properties. While the app is in Testing, only listed test users can sign in —
   forgetting this produces an "access blocked" error at login.

Leave the app in Testing. Publishing triggers Google's verification process,
which you do not need for a local tool. A Testing-mode refresh token expires
after **7 days** — that is the main cost of this path, and the reason the
service account is recommended for anything routine.

## 3. Create OAuth credentials

1. <https://console.cloud.google.com/apis/credentials> → **Create credentials**
   → **OAuth client ID**.
2. Application type: **Desktop app**.
3. Download the JSON and store it privately:

   ```bash
   mkdir -p ~/.config/gsc-mcp
   mv ~/Downloads/client_secret_*.json ~/.config/gsc-mcp/client_secrets.json
   chmod 600 ~/.config/gsc-mcp/client_secrets.json
   ```

## 4. Point the plugin at it

```json
{
  "mcpServers": {
    "gsc-server": {
      "command": "bash",
      "args": ["${CLAUDE_PLUGIN_ROOT}/server/run-server.sh"],
      "env": {
        "GSC_OAUTH_CLIENT_SECRETS_FILE": "/Users/you/.config/gsc-mcp/client_secrets.json",
        "GSC_DATA_STATE": "all",
        "GSC_ALLOW_DESTRUCTIVE": "false"
      }
    }
  }
}
```

Leave `GSC_CREDENTIALS_PATH` and `GSC_SKIP_OAUTH` unset on this path.

## 5. First login

Restart Claude fully (Cmd+Q), then ask:

> Authenticate my Search Console connection

That calls the `reauthenticate` tool, which opens a browser window. Sign in with
the account that owns the properties and grant access. The token is cached in
your OS config directory (override with `GSC_CONFIG_DIR`).

Then verify:

> Which Search Console properties do I have access to?

## When it stops working

An expired or revoked token shows up as auth errors on every call. Fix:

> Authenticate my Search Console connection

If that fails, check in order: the account you signed in with is still a test
user on the consent screen; the client secrets file still exists at the
configured path; the Search Console API is still enabled on the project.

If you find yourself re-authenticating every week, that is the Testing-mode
7-day refresh token limit working as designed. Switch to
[a service account](setup-service-account.md).
