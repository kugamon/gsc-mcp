# Modernization review — the vendored server

A review of `plugins/gsc-seo/server/gsc_server.py` (1,705 lines, 21 tools,
upstream v0.3.3 / commit `b3f2ab8`) against the current Model Context Protocol
specification, the MCP Python SDK, and Google's Search Console API
documentation. Last verified 2026-09-14.

The server works and is actively maintained upstream. Nothing here is a bug
report. It is a list of places where the code predates capabilities that now
exist, and where adopting them would make it measurably faster, cheaper in
tokens, or more correct.

## How claims in this document are supported

Every technical claim carries its evidence, using one of four markers:

| Marker | Means |
| --- | --- |
| **[code]** | Read directly in `gsc_server.py`, with line numbers |
| **[sdk]** | Read in the installed SDK's own source |
| **[probe]** | Demonstrated by running it — command included |
| **[docs]** | Stated in vendor documentation, linked in Sources |

An earlier revision of this document asserted three things that did not survive
checking. They are marked **CORRECTED** below, with what was wrong and what is
actually true, because a review that quietly fixes its own errors teaches the
next reader nothing.

## The constraint this review has to respect

`gsc_server.py` is vendored **byte-identical** and CI verifies its SHA-256
against `server/UPSTREAM.md`. Every finding is therefore tagged with where a fix
can land:

| Tag | Meaning |
| --- | --- |
| **Wrapper** | Fixable here without touching the vendored file |
| **Upstream** | Belongs as a PR to AminForou/mcp-gsc — everyone benefits, we keep the hash check |
| **Fork** | Only achievable by abandoning byte-identical vendoring |

## Where the platform moved

**Spec `2026-07-28`** (final, 28 July 2026) is the largest revision since
launch: a stateless core with the `initialize` handshake and `Mcp-Session-Id`
removed, a formal extensions framework, `Mcp-Method`/`Mcp-Name` routing headers,
`ttlMs`/`cacheScope` on list results, full JSON Schema 2020-12 for tool input
and output schemas, and two official extensions — Tasks and MCP Apps. Roots,
sampling, and MCP-level logging are deprecated; `ping` is removed. **[docs]**

**Python SDK v2** is GA. As of this review `pip install mcp` resolves to
**2.2.0** **[probe]**: `uv run --with "mcp[cli]" python -c "import
importlib.metadata as md; print(md.version('mcp'))"`. `FastMCP` is now
`MCPServer`, `mcp.server.fastmcp.*` moved to `mcp.server.mcpserver.*`, fields
are snake_case, and OpenTelemetry middleware is on by default. **[docs]**

We pin `mcp[cli]==1.27.2` exactly, so none of this reached us. That pin is the
reason v2's release was a non-event here, and it is also why an unpinned
`mcp[cli]` today would silently jump two major versions.

---

## Tier 1 — Correctness and performance

### 1.1 Every tool is `async def` and almost none of them await anything

**Wrapper: no. Upstream: yes. Impact: high. Effort: low.**

**[code]** 21 tools declared `async def`; 4 `await` expressions in the entire
file; 22 blocking `service.…execute()` calls.
`grep -c "^async def" gsc_server.py` → 21, `grep -c "await " gsc_server.py` → 4,
`grep -c "\.execute()" gsc_server.py` → 22.

`google-api-python-client` is synchronous, so every tool call occupies the event
loop for a full HTTPS round trip to Google. On stdio with a single caller this
is mostly invisible. It stops being invisible the moment two things overlap —
`batch_url_inspection` over ten URLs, or any HTTP deployment with more than one
client.

> **CORRECTED.** The previous revision said the fix was to "delete the word
> `async`", because SDK v2 runs sync tools on a worker thread. That is true of
> v2 and **false of the version this server pins**, so the advice would have
> changed nothing.
>
> **[sdk]** In `mcp 1.27.2`, `FuncMetadata.call_fn_with_arg_validation` ends:
> ```python
> if fn_is_async:
>     return await fn(**arguments_parsed_dict)
> else:
>     return fn(**arguments_parsed_dict)      # inline, on the event loop
> ```
> **[sdk]** In `mcp 2.2.0`, `FuncMetadata.call_fn` ends:
> ```python
> if fn_is_async:
>     return await fn(**kwargs)
> return await anyio.to_thread.run_sync(functools.partial(fn, **kwargs))
> ```
> Its docstring says so outright: "A sync function runs on a worker thread."

**The correct fix on the pinned SDK** is to keep the tools `async` and move the
blocking call off the loop:

```python
import anyio

async def _execute(request):
    """Run a blocking googleapiclient request off the event loop."""
    return await anyio.to_thread.run_sync(request.execute)
```

Then each of the 22 sites becomes
`response = await _execute(service.searchanalytics().query(...))`.
**[code]** All 22 are single-line calls, so the edit is mechanical.

Use `anyio`, not `asyncio.to_thread`, for two reasons. **[sdk]** The SDK runs
the server under `anyio.run(...)` (`FastMCP.run`), and **[sdk]** v2 implements
this exact offload with `anyio.to_thread.run_sync` — matching the framework's
own choice keeps it correct under either backend. **[probe]** `anyio` is already
a direct dependency of `mcp` (`anyio>=4.5`), so the import adds nothing to the
dependency tree.

**On efficiency.** A thread hop costs microseconds against a network call that
costs hundreds of milliseconds, so the overhead is noise. It is still a
workaround: `google-api-python-client` has no async interface, and the
genuinely efficient design would issue the HTTP requests natively async. That is
a rewrite of the transport layer, not a patch, and is out of scope here.
**[probe]** anyio's default worker pool is 40 threads
(`anyio.to_thread.current_default_thread_limiter().total_tokens` → 40), which
bounds the blast radius without extra configuration.

### 1.2 Batch inspection is a sequential blocking loop

**Wrapper: no. Upstream: yes. Impact: high. Effort: low.**

**[code]** `batch_url_inspection` iterates at line 733 and
`check_indexing_issues` at line 824, each calling `.execute()` one URL at a
time. Ten URLs is ten serial round trips.

**[code]** Both refuse more than 10 URLs (lines 728, 812) with the message
"Please limit to 10 URLs per batch to avoid API quota issues." **[docs]** The
real per-site quota is **2,000 queries per day and 600 per minute** — the 10-URL
cap is about the serial design being unbearable at larger sizes, not about the
quota.

**Fixed upstream in 0.4.0 for `batch_url_inspection` only.** Issue
[#31](https://github.com/AminForou/mcp-gsc/issues/31) reported 10-URL batches
taking 70–100 s against `sc-domain:` properties and exceeding the MCP client's
60 s timeout. The maintainer resolved it with `asyncio.Semaphore(10)` +
`asyncio.to_thread` + `asyncio.gather`, giving each thread its own service
instance — the right detail, since `googleapiclient` service objects are not
thread-safe.

**[code]** `check_indexing_issues` was not changed and is still a sequential
loop with the same 10-URL cap, so it plausibly has the same timeout. Flagged
upstream in #55 as an observation rather than a reproduced bug. The 10-URL cap
also remains on both, despite the 600 QPM quota now being the only real
constraint.

Bounded concurrency fixes both: a semaphore of 5–10 over the thread offload from
1.1, sized against 600 QPM rather than a round number.

### 1.3 No retry or backoff on 429 and 5xx

**Wrapper: no. Upstream: yes. Impact: medium-high. Effort: low.**

**[code]** Quota conditions are recognised (lines 386, 397, 440, 451) and turned
into strings such as `"Error: API quota exceeded. Please try again later."` —
handed to the model, which then decides whether to retry, and typically retries
at once.

**[docs]** Search Analytics carries two independent quotas: QPS/QPM/QPD
(1,200 QPM per site) **and** a separate *load* quota measured in 10-minute and
1-day windows, where cost rises with date range and with grouping or filtering
by page and query. Retrying a load-quota rejection immediately makes it worse.

Exponential backoff with jitter belongs in the client, not in the model's
judgment.

### 1.4 Date ranges are built from naive local time

**Wrapper: partially. Upstream: yes. Impact: medium. Effort: trivial.**

**[code]** `datetime.now().date()` at lines 482, 910, 1021, 1023, 1298 — naive,
in the server process's local timezone.

**[docs]** The API reference is explicit: `startDate` and `endDate` are
"in YYYY-MM-DD format, **in PT time (UTC - 7:00/8:00)**", and response metadata
timestamps are "in the `America/Los_Angeles` time zone."

So a caller in London asking for "the last 28 days" at 09:00 local gets a window
shifted a day against what Search Console shows them — which reads to the user
as the API being wrong. Anchor the window to `America/Los_Angeles` and echo the
resolved dates in the response so any remaining offset is visible.

### 1.5 The API reports which data is incomplete, and the server discards it

**Wrapper: partially. Upstream: yes. Impact: medium. Effort: low.**
*(New finding — missed by the previous revision.)*

**[docs]** When `dataState` is `all`, a Search Analytics response may carry a
`metadata` object containing `first_incomplete_date` — "the first date for which
the data is still being collected and processed" — and, for hourly grouping,
`first_incomplete_hour`. Google states that "all values after the
`first_incomplete_date` may still change noticeably."

**[code]** No tool reads `metadata`; every one builds its result from
`response.get("rows", [])` only.

This matters because our own skills currently tell Claude that "the last 2–3
days are provisional" — a rule of thumb standing in for a value the API returns
exactly. Surfacing it would replace a guess with a fact, and would let a report
mark precisely where the provisional region starts.

### 1.6 ~~`sort_by` is accepted and silently ignored~~ — FIXED UPSTREAM in 0.4.0

**Reported as AminForou/mcp-gsc#54 on 2026-09-14, fixed 2026-09-15.** The
maintainer removed the dead `orderBy` and sorts client-side after fetching.

**The trap survives in a subtler form, and the skill still covers it.** Google
only ever returns rows sorted by clicks descending, so a client-side sort
reorders the page you received without changing which rows you received. Asking
for `sort_by=impressions` on a 200-row pull gives the highest-impression queries
*among the 200 with the most clicks* — a zero-click query with 500 impressions
was never in the set. Filters remain the only way to reach it. Upstream
documents this honestly in a code comment: "Sorting applies within the returned
page of rows."

One instance of the same dead field remains in `get_search_by_page_query`;
reported as #55.

The original finding is preserved below.

---

**[code]** `get_advanced_search_analytics` builds
`request["orderBy"] = [{"metric": ..., "direction": ...}]` (lines 1048–1058).

**[docs]** The Search Analytics API request body has no `orderBy` member. Its
documented fields are `startDate`, `endDate`, `dimensions`, `type`,
`dimensionFilterGroups`, `aggregationType`, `rowLimit`, `startRow` and
`dataState`, and the reference states results are sorted by click count
descending. Google discards the unknown field.

**[probe]** Requesting `sort_by=position, sort_direction=ascending` returns
positions in the order 9.4, 18.6, 12.4, 11.0 — identical to the unsorted call.

The tool therefore reports a sort it did not perform, which is worse than an
error: a caller asking for "top by impressions" receives a clicks-ranked list
and has no signal that anything went wrong.

The consequence compounds. With ordering fixed to clicks, a large `row_limit`
returns every query that has clicks and fills the remainder with **zero-click
queries in arbitrary order**. High-impression zero-click queries — precisely
what an SEO analysis is looking for — are effectively unreachable. In real use
this concealed a 500-impression, position-12.5 query that was the largest single
opportunity on the site.

**Fix, upstream:** either drop the parameter and document that the API sorts by
clicks, or keep it and sort client-side after fetching — which is only honest if
the tool also fetches enough rows for a client-side sort to mean anything.
Silently accepting it is the one option that should not remain.

**Fix, here:** done. The `gsc-seo-analysis` skill documents the behaviour at the
point of use and prescribes filtered pulls, which do work, as the workaround.

---

## Tier 2 — What the model actually receives

### 2.1 Structured data is returned as a JSON string inside a string schema

**Wrapper: no. Upstream: yes. Impact: high. Effort: medium.**

**[code]** 13 of 21 tools build a dict and return `json.dumps(...)` under a
`-> str` annotation.

> **CORRECTED.** The previous revision said this produces "no `outputSchema`
> and no `structuredContent`." That is wrong — it produces both, and what they
> contain is the actual problem.
>
> **[probe]** Registering two tools on `mcp 1.27.2`, one returning
> `json.dumps({...})` under `-> str` and one returning a Pydantic model:
>
> ```
> returns_json_string  outputSchema: {"properties":{"result":{"type":"string"}},...}
>                      structuredContent: {"result": "{\"site_url\": \"…\", \"rows\": [{…}]}"}
> returns_model        outputSchema: {"$defs":{"Row":{…}},"properties":{"site_url":…}}
>                      structuredContent: {"site_url":"…","rows":[{"query":"a","clicks":1}]}
> ```
>
> The SDK wraps a `-> str` return in `{"result": <string>}`. So the payload is
> **JSON encoded as a string, nested inside JSON** — double-encoded, with every
> quote escaped. The declared schema says "this tool returns a string," which is
> true and useless: no client can validate the contents, and the escaping costs
> tokens on every single response.

Returning a Pydantic model, dataclass, or TypedDict fixes both halves at once —
a real schema generated from the return annotation, and clean structured
content. **[docs]** Under spec 2026-07-28 output schemas are full JSON Schema
2020-12 and `structuredContent` may be any JSON value, so no shape is out of
reach.

This is the highest-value change in the file, and on the "most efficient code"
axis it is also the cheapest win: it removes a whole layer of escaping from
every response.

### 2.2 Eight tools do not follow the pattern the other thirteen use

**Wrapper: no. Upstream: yes. Impact: medium. Effort: low.**

**[code]** `add_site`, `delete_site`, `submit_sitemap`, `delete_sitemap`, and
`reauthenticate` return assembled prose or plain sentences;
`get_capabilities` returns a formatted text block; `get_creator_info` returns a
string.

> **CORRECTED.** The previous revision listed `manage_sitemaps` among the
> inconsistent tools. **[code]** It is a router — it `return await`s
> `list_sitemaps_enhanced`, `get_sitemap_details`, and the others, so its output
> format is whatever they produce. It is not a separate inconsistency.

**[docs]** Upstream's own `CLAUDE.md` already states the intended rule:
"Return `json.dumps(result)` not formatted text strings (LLMs work better with
structured data)." These eight predate it. Whatever 2.1 settles on should apply
to all 21.

### 2.3 Errors are returned as successful results

**Wrapper: no. Upstream: yes. Impact: high. Effort: medium.**

**[code]** 40 `return f"Error…"` sites; 32 `except Exception` handlers against
8 `raise` statements. Every failure arrives as a normal successful result whose
text begins with "Error". Nothing sets `isError`.

Consequences: a client cannot distinguish failure from data without
string-matching; retry logic cannot trigger; failures are invisible to tracing;
and a genuine query containing the word "Error" is indistinguishable from a
fault.

**[docs]** Upstream's `CLAUDE.md` documents this as the house pattern —
"Handle `HttpError` and return a plain string error message on failure" — so
changing it is a convention change, not a bug fix, and should be raised as such.

**Partially resolved upstream in 0.4.0.** Raised as
[#53](https://github.com/AminForou/mcp-gsc/issues/53); the maintainer narrowed
the bare `except:` clauses to `except Exception:` and **declined the isError
change**, keeping the documented string-error convention. That is his call on
his project's conventions, and raising it as a discussion rather than a PR was
the right way to find that out. The analysis above stands as a reason to prefer
error semantics in anything we build ourselves.

### 2.4 No tool annotations

**Wrapper: no. Upstream: yes. Impact: medium. Effort: trivial.**

**[code]** Every tool registers as a bare `@mcp.tool()`.
**[sdk]** `FastMCP.tool` in 1.27.2 already accepts
`name, title, description, annotations, icons, meta, structured_output`, and
**[sdk]** `mcp.types.ToolAnnotations` exposes `title`, `readOnlyHint`,
`destructiveHint`, `idempotentHint`, `openWorldHint`. All unused.

**[code]** Classifying all 21 by whether they mutate anything: **15 are
read-only**, 4 write (`add_site`, `delete_site`, `submit_sitemap`,
`delete_sitemap`), 1 writes auth state (`reauthenticate`), and 1 is a router
(`manage_sitemaps`). **[code]** Exactly 3 are gated by `GSC_ALLOW_DESTRUCTIVE`
— `add_site` (line 355), `delete_site` (line 416), `delete_sitemap` (line 1535).

So: `readOnlyHint` on the 15, `destructiveHint` on the 3 gated ones, and
neither on `submit_sitemap` — it writes but is not destructive, which is
precisely the distinction the annotations exist to express and which a single
environment flag cannot. `idempotentHint` on the analytics tools lets clients
cache and retry safely. Hosts could then apply their own confirmation UX instead
of depending solely on this plugin's flag.

### 2.5 Twenty-one tools, several of them the same tool twice

**Wrapper: partially — our skills steer selection. Upstream: yes.
Impact: medium. Effort: medium.**

**[code]** Six sitemap tools over four operations (`get_sitemaps`,
`list_sitemaps_enhanced`, `get_sitemap_details`, `submit_sitemap`,
`delete_sitemap`, `manage_sitemaps`, the last a router over the others). Three
URL-inspection tools that differ only in cardinality and filtering. Two search
analytics tools that differ by capability, not purpose — the "advanced" one at
165 lines is the largest in the file.

The split exists for an avoidable reason. **[code]** `get_search_analytics`
clamps `rowLimit` to 500 (line 493). **[docs]** The API's own valid range is
**1–25,000 with a default of 1,000**. The 500 cap is self-imposed, and
`get_advanced_search_analytics` exists partly to escape it.

Consolidating to roughly a dozen richer tools would cut the tool-list context
every request carries and remove a class of wrong-tool selection. It is a
breaking change for anyone whose prompts name the old tools.

### 2.6 No caching, and Google explicitly asks for it

**Wrapper: partially. Upstream: yes. Impact: medium. Effort: low.**

**[code]** No `lru_cache`, no TTL, no memoisation anywhere;
`grep -in "cache\|lru_cache" gsc_server.py` returns only comments and the
`cache_discovery=False` argument. `list_properties` opens nearly every workflow,
changes perhaps twice a year, and is re-fetched every time.

**[docs]** Under Search Analytics load quota, Google's own guidance is to
"avoid requerying the same data (for example, querying all data for last month
over and over)." The load quota is the one most likely to bite a heavy user, and
caching is the documented mitigation.

**[docs]** Spec 2026-07-28 adds `ttlMs` and `cacheScope` to list results, so a
server can tell clients how long an answer stays fresh.

> **CORRECTED.** The previous revision called `cache_discovery=False`
> (lines 152, 224) "wasteful as a permanent setting," implying a per-call HTTP
> fetch of the discovery document.
>
> **[probe]** It costs nothing. With `socket.socket` patched to raise,
> `build("searchconsole", "v1", credentials=…, cache_discovery=False)` still
> succeeds in 0.001 s — `google-api-python-client` uses a bundled static
> discovery document and makes no network call. The setting only suppresses a
> file-cache warning, and `get_gsc_service()` is cheap. **The 22 `.execute()`
> calls are the only blocking network I/O in the file.**

---

## Tier 3 — Platform features that postdate this design

### 3.1 Tasks extension for long-running work

**Wrapper: no. Upstream: yes. Impact: high for large sites. Effort: high.**

**[docs]** A server can answer `tools/call` with a task handle and let the
client drive `tasks/get`, `tasks/update`, and `tasks/cancel`. Task creation is
server-directed; `tasks/list` was removed because it cannot be scoped safely
without sessions.

Indexing audits are the natural fit. Today, a 5,000-page audit is 500 separate
calls the model has to orchestrate, because a synchronous call cannot credibly
run for minutes. As a task it becomes one call that reports progress, paces
itself against 600 QPM internally, and can be cancelled.

**[docs]** Tasks was redesigned when it graduated from experimental core feature
to extension — anything built against the `2025-11-25` API needs migrating.

### 3.2 Elicitation instead of an environment flag

**Wrapper: no. Upstream: yes. Impact: medium. Effort: medium.**

`GSC_ALLOW_DESTRUCTIVE` is binary and set long before the dangerous moment: off
and the tool is unusable, on and an agent can delete a property irreversibly
with no confirmation. It exists because there was no in-protocol way to ask.

**[docs]** There is now. The server returns an `InputRequiredResult` carrying
what it still needs plus an opaque `requestState`; the client collects the
answer and re-issues the call. "Delete `sc-domain:example.com`? This cannot be
undone" becomes a prompt at the moment of the action, naming the specific
target.

Keep the flag as a default for hosts that do not implement the extension. A
confirmation attached to the operation is strictly better than a flag set weeks
earlier for a different reason.

### 3.3 MCP Apps for reports

**Wrapper: no. Upstream: unlikely to be accepted. Impact: speculative.
Effort: high.**

**[docs]** Servers can ship interactive HTML that hosts render in a sandboxed
iframe, with UI-initiated actions going through the same consent path as a
direct tool call.

Listed for completeness, not recommended. It is a poor fit for an upstream
project scoped to data access, and this repo already has a better answer for
visual output: build the report as an artifact from what the tools return.

### 3.4 Streamable HTTP instead of SSE

**Wrapper: no. Upstream: yes. Impact: low for us. Effort: trivial.**

**[code]** `main()` accepts only `stdio` and `sse` (line ~1672), and disables
DNS-rebinding protection outright (line 1693) to make the remote path work.

> **CORRECTED.** The previous revision implied this needed an SDK upgrade and
> rated the effort medium. **[sdk]** `FastMCP.run` in the pinned 1.27.2 already
> accepts `transport: Literal["stdio", "sse", "streamable-http"]`. Supporting
> the modern transport is adding one branch to upstream's `main()` — the SDK
> support is already installed and paid for.

**[docs]** SSE was deprecated in spec `2025-03-26` in favour of Streamable HTTP.
We run stdio, so this costs us nothing today; it matters for any hosted
deployment, and disabling a security control to prop up a deprecated transport
is the wrong end state regardless.

### 3.5 SDK v2 migration

**Wrapper: the pin is ours. Upstream: the port is theirs.
Impact: medium. Effort: medium.**

**[docs]** The port is mechanical — `FastMCP` → `MCPServer`, module path,
snake_case attributes — and it brings 1.1 for free, adds OpenTelemetry spans by
default, and serves both protocol revisions from one deployment so older hosts
keep working.

Our exact pin means there is no urgency. This can wait for upstream.

---

## Tier 4 — Hygiene

| Item | Detail |
| --- | --- |
| **Single-module layout** | **[code]** 1,705 lines in one file; six tools over 78 lines, the largest 165. A package (`auth`, `analytics`, `indexing`, `sitemaps`) would make it navigable and testable. **Upstream.** |
| ~~**Tests are not vendored**~~ | **Done, 2026-09-14.** Upstream's 780-line `test_gsc_server.py` is now vendored beside the server, hash-pinned in `UPSTREAM.md`, and run by CI — 43 tests, mocked, no credentials. CI now proves a tool *works*, not just that the server starts. |
| **Bare `except:`** | **[code]** Lines 760, 1506, 1517. **Upstream.** |
| **DNS-rebinding protection disabled** | **[code]** Line 1693, unconditional on the SSE path. Should be opt-in with a documented origin allowlist. **Upstream.** |
| **No structured logging** | Everything is stderr text. **[docs]** MCP-level logging is deprecated in favour of OpenTelemetry, which v2 emits by default. **Upstream.** |

---

## What to do, in order

**Here, needing nobody's permission:**

1. ~~Vendor `test_gsc_server.py` and run it in CI.~~ **Done 2026-09-14.**
2. Keep the skills steering tool selection — that is already mitigating 2.5.
3. Consider replacing the skills' "last 2–3 days are provisional" rule of thumb
   with `metadata.first_incomplete_date` once 1.5 lands upstream.

**As upstream PRs, highest value first:**

3. **Thread-offload the remaining 21 `.execute()` calls** (1.1). Open as
   AminForou/mcp-gsc#52, **rebased onto 0.4.0 on 2026-09-15** — 0.4.0 rewrote
   `batch_url_inspection`, which the original patch touched. Now 21 sites
   rather than 22, with `_inspect_single_url` deliberately left synchronous
   because it already runs in a worker thread. Measured 1.27 s → 0.28 s for 5
   concurrent calls at 250 ms latency; regression test verified to fail on
   revert.
4. **Typed returns with output schemas** (2.1 + 2.2). Removes double-encoding
   from every response and gives clients something to validate.
5. **Surface `metadata.first_incomplete_date`** (1.5). Small, and it replaces a
   rule of thumb with a fact the API already returns.
6. **Tool annotations** (2.4). An afternoon.
7. ~~**Proper error semantics**~~ (2.3). **Raised 2026-09-14 as
   AminForou/mcp-gsc#53**, as a discussion rather than a PR because it
   contradicts upstream's documented pattern. Probing both patterns showed the
   human-readable message survives either way, so it is not the trade it
   looks like.
8. **Bounded concurrency and backoff** (1.2 + 1.3). Removes the artificial
   10-URL cap.
9. **Tasks extension** (3.1). The one that changes what the server can do.

**Do not:**

- Fork to obtain items 3–9. Every one is generic; none is Kugamon-specific.
- Unpin `mcp`. **[probe]** An unpinned `mcp[cli]` resolves to 2.2.0 today.
- Chase MCP Apps (3.3). Artifacts cover visual reporting better.

## If upstream declines

The question becomes whether a fork is worth permanent ownership of 1,705 lines.
Today the honest answer is no: the server works, and everything above is a
quality improvement rather than a defect. Revisit if 1.1 or 2.3 is declined —
those two are the ones that will eventually bite a real user.

## Sources

**Protocol and SDK**

- [The 2026-07-28 MCP Specification Release Candidate](https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/) — stateless core, Tasks, MCP Apps, JSON Schema 2020-12, deprecations
- [Transports — MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)
- [MCP Python SDK v2: what is new](https://pydantic.dev/articles/mcp-python-sdk-v2-beta) — `MCPServer` rename, worker-thread dispatch, OpenTelemetry
- [Structured Output — MCP Python SDK](https://py.sdk.modelcontextprotocol.io/servers/structured-output/)
- [modelcontextprotocol/python-sdk releases](https://github.com/modelcontextprotocol/python-sdk/releases)

**Google Search Console**

- [Search Analytics: query — API reference](https://developers.google.com/webmaster-tools/v1/searchanalytics/query) — `startDate`/`endDate` in PT, `rowLimit` 1–25,000, `metadata.first_incomplete_date`
- [Usage Limits — Search Console API](https://developers.google.com/webmaster-tools/limits) — URL inspection 2,000 QPD / 600 QPM per site; Search Analytics 1,200 QPM; load quota and "avoid requerying the same data"
- [Performance report: About the data](https://support.google.com/webmasters/answer/17011364) — preliminary data, property vs page aggregation

**Upstream project**

- [AminForou/mcp-gsc](https://github.com/AminForou/mcp-gsc) — the vendored server; `CLAUDE.md` documents the `json.dumps` and string-error conventions
