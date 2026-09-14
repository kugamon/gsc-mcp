# Modernization review — the vendored server

A review of `plugins/gsc-seo/server/gsc_server.py` (1,705 lines, 21 tools,
upstream v0.3.3 / commit `b3f2ab8`) against the current Model Context Protocol
specification and Python SDK, as of September 2026.

The server works and is well-maintained upstream. Nothing here is a bug report.
It is a list of places where the code predates protocol features that now exist,
and where those features would make it measurably better.

## The constraint this review has to respect

`gsc_server.py` is vendored **byte-identical** and CI verifies its SHA-256
against `server/UPSTREAM.md`. That is a deliberate choice (see
`docs/architecture.md`), and it means no finding below can be "just patch it."
Every item is tagged with where it can actually land:

| Tag | Meaning |
| --- | --- |
| **Wrapper** | Fixable in this repo without touching the vendored file |
| **Upstream** | Belongs as a PR to [AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc) — everyone benefits, we keep the hash check |
| **Fork** | Only achievable by abandoning byte-identical vendoring |

Prefer Upstream. A fork means owning 1,705 lines of someone else's code
forever, and re-syncing becomes a merge instead of a copy.

## Where the protocol moved

Two releases happened after this server's design was set.

**Spec `2026-07-28`** (final, July 2026) is the largest revision since launch: a
stateless core with the `initialize` handshake and `Mcp-Session-Id` removed, a
first-class extensions framework, `Mcp-Method`/`Mcp-Name` routing headers,
`ttlMs`/`cacheScope` on list results, full JSON Schema 2020-12 for tool input
and output schemas, and two official extensions — **Tasks** (long-running work)
and **MCP Apps** (server-rendered HTML UIs). Roots, sampling, and MCP-level
logging are deprecated; `ping` is removed.

**Python SDK v2.0.0** went GA in August 2026. `FastMCP` is now `MCPServer`,
`mcp.server.fastmcp.*` moved to `mcp.server.mcpserver.*`, fields are snake_case,
wire types split into a separate `mcp-types` distribution, OpenTelemetry
middleware is on by default, and — the one that matters most here — **sync `def`
tools now run on a worker thread instead of blocking the event loop.**

We pin `mcp[cli]==1.27.2`, so none of this has broken us. It does mean we are
now on the previous major line.

---

## Tier 1 — Correctness and performance

### 1.1 Every tool is `async def` and almost none of them await anything

**Wrapper: no. Upstream: yes. Impact: high. Effort: trivial.**

21 tools are declared `async def`. There are 4 `await` expressions in the entire
file, and 22 blocking `service....execute()` calls. `google-api-python-client`
is synchronous, so every tool call blocks the event loop for the full duration
of an HTTPS round trip to Google.

On stdio with one client this is mostly invisible. It stops being invisible the
moment anything runs concurrently — `batch_url_inspection` over ten URLs, or any
HTTP deployment serving more than one caller.

The fix under SDK v1 is `asyncio.to_thread(...)` around each `.execute()`.
The fix under **v2 is to delete the word `async`** — v2 runs sync tools on a
worker thread automatically. A 21-line diff that makes the whole file correct is
an unusually good upstream PR.

### 1.2 Batch inspection is a sequential blocking loop

**Wrapper: no. Upstream: yes. Impact: high. Effort: low.**

`batch_url_inspection` (line 733) and `check_indexing_issues` (line 824) iterate
URLs and call `.execute()` one at a time. Ten URLs is ten serial round trips —
several seconds of wall clock where one second would do.

The URL Inspection quota is roughly 600/minute and 2,000/day per property, so
concurrency has to be bounded, not unlimited: a semaphore of 5–10 against a
thread pool. Both tools cap input at 10 URLs (lines 728, 812) specifically to
avoid quota trouble — a cap that exists because the serial design makes larger
batches unbearable, not because the API requires it.

### 1.3 No retry or backoff on 429 and 5xx

**Wrapper: no. Upstream: yes. Impact: medium-high. Effort: low.**

Quota errors are recognized (lines 386, 397, 440, 451) and turned into
`"Error: API quota exceeded. Please try again later."` — a string handed to the
model, which then guesses whether to retry and usually retries immediately.

A transient 429 or 503 against a quota-limited API is the textbook case for
exponential backoff with jitter, handled in the client rather than delegated to
the model's judgment.

### 1.4 Date ranges use naive local time

**Wrapper: partially. Upstream: yes. Impact: low-medium. Effort: trivial.**

`datetime.now().date()` at lines 482, 910, 1021, 1023, 1298. Search Console's
day boundaries are fixed in Pacific Time regardless of where the server runs, so
a user in Europe asking for "the last 28 days" at 09:00 local gets a window
shifted by a day against what the GSC dashboard shows — the kind of discrepancy
that reads as "the API is wrong."

Anchor the range to the property's reporting timezone, and state the resolved
window in the response so the offset is visible rather than mysterious.

---

## Tier 2 — What the model actually receives

### 2.1 Structured output is returned as a string

**Wrapper: no. Upstream: yes. Impact: high. Effort: medium.**

13 of 21 tools do the right thing and build a dict — then return
`json.dumps(...)` with a `-> str` annotation. The SDK sees a string, so the tool
gets no `outputSchema` and the result carries no `structuredContent`. The model
receives JSON-as-text and has to parse it, and no client can validate it.

The installed SDK already supports this properly: return a Pydantic model,
dataclass, or TypedDict and the framework populates `structured_content` and
generates the output schema from the return annotation. Under spec 2026-07-28,
output schemas are full JSON Schema 2020-12 and `structuredContent` may be any
JSON value, so there is no shape this data cannot express.

This is the single highest-value change in the file. It turns 13 tools from
"here is some text that happens to be JSON" into typed, validated results.

### 2.2 Eight tools are inconsistent with the other thirteen

**Wrapper: no. Upstream: yes. Impact: medium. Effort: low.**

`add_site`, `submit_sitemap`, and `delete_sitemap` return assembled prose.
`get_capabilities`, `delete_site`, `manage_sitemaps`, `get_creator_info`, and
`reauthenticate` return plain strings. A model working across the tool set gets
JSON from some calls and sentences from others, with nothing signalling which.

Whatever 2.1 settles on, it should apply to all 21.

### 2.3 Errors are returned as successful results

**Wrapper: no. Upstream: yes. Impact: high. Effort: medium.**

40 `return f"Error..."` sites across the file, and 32 `except Exception`
handlers against 8 `raise` statements. Every failure comes back as a normal
successful tool result whose text begins with "Error". Nothing sets `isError`.

The consequences are concrete: a client cannot distinguish failure from data
without string-matching, retry logic cannot trigger, errors are invisible to
tracing, and a query that legitimately returns the word "Error" is
indistinguishable from a failure. Raising a tool error — or returning a result
with `is_error` set — costs nothing and makes failure machine-readable.

Note also three bare `except:` clauses (lines 760, 1506, 1517), which swallow
`KeyboardInterrupt` and `SystemExit` along with everything else.

### 2.4 No tool annotations

**Wrapper: no. Upstream: yes. Impact: medium. Effort: trivial.**

Every tool is registered as a bare `@mcp.tool()`. The installed SDK's `tool()`
already accepts `name`, `title`, `description`, `annotations`, `icons`, `meta`,
and `structured_output` — all unused.

`readOnlyHint` on the 18 read-only tools and `destructiveHint` on
`delete_site`, `delete_sitemap`, and `add_site` would let hosts apply their own
confirmation UX instead of relying solely on this plugin's
`GSC_ALLOW_DESTRUCTIVE` environment flag. `idempotentHint` on the analytics
tools would let clients cache and retry safely.

### 2.5 Twenty-one tools is a large surface for what the API offers

**Wrapper: partially — we choose what to document and steer toward.
Upstream: yes. Impact: medium. Effort: medium.**

Several tools overlap:

- `get_sitemaps`, `list_sitemaps_enhanced`, `get_sitemap_details`,
  `submit_sitemap`, `delete_sitemap`, and `manage_sitemaps` — six tools over
  four operations, one of which (`manage_sitemaps`) is a router over the others.
- `get_search_analytics` and `get_advanced_search_analytics` differ by
  capability, not by purpose. The "advanced" one is 165 lines, the largest tool
  in the file.
- `inspect_url_enhanced`, `batch_url_inspection`, and `check_indexing_issues`
  are one URL, several URLs, and several URLs filtered to problems.

Every tool costs context in the model's tool list and adds a selection decision.
The `_enhanced` and `_advanced` suffixes are archaeology — they exist because
the simple version shipped first. Consolidating to roughly a dozen tools with
richer parameters would read better and choose better, though it is a breaking
change for anyone with prompts naming the old tools.

Until upstream does anything here, this repo mitigates it: the skills tell
Claude which tool to reach for, which is most of the practical benefit.

### 2.6 No caching anywhere

**Wrapper: partially. Upstream: yes. Impact: medium. Effort: low.**

`list_properties` is the first call in nearly every workflow and its answer
changes maybe twice a year. It is re-fetched every time. The discovery document
is fetched with `cache_discovery=False` (lines 152, 224) — correct for avoiding
the file_cache warning, wasteful as a permanent setting.

Spec 2026-07-28 adds `ttlMs` and `cacheScope` on list and resource-read results
precisely for this, so clients can be told how long an answer stays fresh.

---

## Tier 3 — Platform features that did not exist when this was written

### 3.1 Tasks extension for long-running work

**Wrapper: no. Upstream: yes. Impact: high for large sites. Effort: high.**

Indexing audits are the natural shape for this. Today the tools cap at 10 URLs
per call because a synchronous call cannot credibly run for minutes; a real
audit of a 5,000-page site is therefore 500 calls that the model has to
orchestrate.

Under the Tasks extension a server can answer `tools/call` with a task handle
and let the client drive `tasks/get`, `tasks/update`, and `tasks/cancel`. "Audit
every URL in this sitemap" becomes one call that reports progress, respects the
600/minute quota internally, and can be cancelled. This is the feature that
would change what the server is capable of rather than how tidy it is.

Note that Tasks was redesigned when it moved from experimental core feature to
extension — anyone who built against the `2025-11-25` API has to migrate.

### 3.2 Elicitation instead of an environment flag

**Wrapper: no. Upstream: yes. Impact: medium. Effort: medium.**

`GSC_ALLOW_DESTRUCTIVE` is a blunt instrument: off and the tool is unusable, on
and an agent can delete a property irreversibly with no confirmation. It exists
because there was no in-protocol way to ask a human.

There is now. Under 2026-07-28 the server returns an `InputRequiredResult`
carrying what it needs plus an opaque `request_state`; the client collects the
answer and re-issues the call. "Delete the property `sc-domain:example.com`?
This cannot be undone" becomes a real prompt at the moment of the action,
scoped to the specific target.

Keep the env flag as a belt-and-braces default for hosts that do not implement
the extension. But a confirmation attached to the operation is strictly better
than a flag set weeks earlier for a different reason.

### 3.3 MCP Apps for reports

**Wrapper: no. Upstream: unlikely to be accepted. Impact: speculative.
Effort: high.**

MCP Apps lets a server ship an interactive HTML interface that the host renders
in a sandboxed iframe. A keyword report with sortable columns and a
position-over-time chart is a better artifact than a Markdown table.

Listed for completeness, not recommended. It is the most speculative item here,
it is a poor fit for an upstream project whose scope is data access, and this
repo already has a better answer for visual output: build the report as an
artifact from the data the tools return.

### 3.4 Streamable HTTP instead of SSE

**Wrapper: no. Upstream: yes. Impact: low for us, high for remote deployments.
Effort: medium.**

`main()` (line ~1672) supports `stdio` and `sse`. SSE was deprecated in spec
`2025-03-26` in favour of Streamable HTTP, and the code already carries scar
tissue from the gap — it disables DNS-rebinding protection outright
(line 1693) to make the remote path work at all.

We run stdio, so this costs us nothing today. It matters if a hosted deployment
is ever wanted, and disabling a security control to work around a deprecated
transport is the wrong end state either way.

### 3.5 SDK v2 migration

**Wrapper: the pin is ours. Upstream: the port is theirs.
Impact: medium. Effort: medium.**

v2 is GA and v1 is now the previous line. The port is mechanical — `FastMCP` →
`MCPServer`, module path, snake_case attributes — and it brings 1.1 for free
(sync tools move to a worker thread), plus OpenTelemetry spans by default, plus
the ability to serve both protocol revisions from one deployment.

Our `mcp[cli]==1.27.2` pin is exact, so v2's release cannot surprise us. That is
the pin doing its job, and it is also the reason there is no urgency: this can
wait until upstream moves.

---

## Tier 4 — Hygiene

| Item | Detail |
| --- | --- |
| **Single-module layout** | 1,705 lines in one file, with six tools over 78 lines each and the largest at 165. A package (`auth.py`, `analytics.py`, `indexing.py`, `sitemaps.py`) would make the file navigable and testable. **Upstream.** |
| **Tests are not vendored** | Upstream ships a 780-line `test_gsc_server.py`. We copied only `gsc_server.py`, so our CI proves the server *starts* but never that a tool *works*. Vendoring the test file costs nothing and closes a real gap. **Wrapper — do this.** |
| **Bare `except:`** | Lines 760, 1506, 1517 swallow `KeyboardInterrupt` and `SystemExit`. **Upstream.** |
| **DNS-rebinding protection disabled** | Line 1693, unconditionally on the SSE path. Should be an explicit opt-in with a documented origin allowlist. **Upstream.** |
| **No structured logging** | Everything goes to stderr as text. SDK v2 emits OpenTelemetry spans by default; MCP-level logging is deprecated in favour of exactly that. **Upstream.** |

---

## What to do, in order

**Now, in this repo — no fork, no upstream dependency:**

1. Vendor `test_gsc_server.py` and run it in CI. Our smoke test proves the
   server starts; nothing currently proves a tool returns the right thing.
2. Keep the skills steering tool selection. That is already mitigating 2.5.

**As upstream PRs, highest value first:**

3. **Drop `async` / wrap in `asyncio.to_thread`** (1.1). Smallest diff, largest
   correctness win, uncontroversial.
4. **Typed returns with output schemas** (2.1 + 2.2). The change that most
   improves what the model receives.
5. **Proper error semantics** (2.3). Cheap, and it unblocks retry and tracing.
6. **Tool annotations** (2.4). An afternoon.
7. **Bounded concurrency and backoff** (1.2 + 1.3). Removes the artificial
   10-URL cap.
8. **Tasks extension** (3.1). The one that changes what the server can do.

**Do not:**

- Fork to get items 3–8. Every one of them is a clean upstream contribution, and
  the maintainer is active — the most recent commit is a dependency-pinning fix
  for exactly the kind of breakage this repo cares about.
- Unpin `mcp` to pick up v2 early. The pin is why v2's GA release was a
  non-event for us.
- Chase MCP Apps (3.3). Artifacts already cover visual reporting, better.

## If upstream does not want these

Then the question becomes whether a fork is worth 1,705 lines of permanent
maintenance. The honest answer today is no: the server works, and every item
above is a quality improvement rather than a defect. Revisit if 1.1 or 2.3 is
declined, since those two are the ones that will eventually bite a real user.

## Sources

- [The 2026-07-28 MCP Specification Release Candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/)
- [MCP Python SDK v2 beta: what is new and how to try it](https://pydantic.dev/articles/mcp-python-sdk-v2-beta)
- [Transports — MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)
- [Structured Output — MCP Python SDK](https://py.sdk.modelcontextprotocol.io/servers/structured-output/)
