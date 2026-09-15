---
name: gsc-seo-analysis
plugin: gsc-seo
version: 1.2.0
description: >
  Analyze Google Search Console data and turn it into SEO decisions. Use when the
  user asks to "analyze SEO performance", "check search console data", "review
  keyword rankings", "check GSC", "SEO report", "search analytics", "which
  keywords are we close to ranking for", "why did traffic drop", "compare search
  periods", "keyword analysis", "top pages", or any question about how a site is
  performing in Google search. For indexing, sitemap, and crawl problems, use the
  gsc-indexing-diagnostics skill instead.
---

# Google Search Console — SEO analysis

How to pull the right Search Console data, read it correctly, and turn it into
recommendations someone can act on.

## Before anything else

1. **Call `get_capabilities`.** It reports auth status in one call. If it says
   not authenticated, stop and work through `docs/troubleshooting.md` rather
   than letting every subsequent tool fail one at a time.
2. **Call `list_properties`.** Never guess a `site_url`. The exact string
   matters and there are two shapes:
   - `sc-domain:example.com` — a domain property, covers every subdomain and
     both protocols.
   - `https://www.example.com/` — a URL-prefix property, covers exactly that
     prefix. The trailing slash is part of the string.
   If the user has several, ask which one — or, if the site is obvious from
   context, state which you picked and move on.
3. **Load the site profile if one exists.** See the `gsc-site-profile` skill.
   A profile supplies the brand terms, competitor names, priority pages, and
   keyword categories that make a report specific instead of generic. Without
   one, the analysis below still works; it is just less opinionated.

## The tools, grouped by what they answer

### Orientation
| Tool | Answers |
| --- | --- |
| `get_capabilities` | What can this server do, and am I authenticated? |
| `list_properties` | Which sites do I have access to, and what are their exact URLs? |
| `get_site_details` | Who verified this property and how? |

### Performance
| Tool | Answers | Notes |
| --- | --- | --- |
| `get_performance_overview` | How is the site doing overall? | Summary + daily trend. Start here. |
| `get_search_analytics` | What are the top queries / pages / countries / devices? | `dimensions`, `days`, `row_limit` (max 500). |
| `get_advanced_search_analytics` | Same, with **filters** and pagination | Up to 25,000 rows. Search types: WEB, IMAGE, VIDEO, NEWS, DISCOVER. **`sort_by` is accepted and silently ignored** — see Tool limitations. |
| `compare_search_periods` | What changed between two date ranges? | The drop/gain diagnosis tool. |
| `get_search_by_page_query` | Which queries drive traffic to *this* page? | The page-level workhorse. |

### Indexing
`inspect_url_enhanced`, `batch_url_inspection` (up to 10 URLs), and
`check_indexing_issues`. Covered in the `gsc-indexing-diagnostics` skill.

### Sitemaps
`get_sitemaps`, `list_sitemaps_enhanced`, `get_sitemap_details`,
`manage_sitemaps`. Also in `gsc-indexing-diagnostics`.

### Destructive — disabled by default
`add_site`, `delete_site`, and sitemap deletion via `manage_sitemaps` refuse to
run unless `GSC_ALLOW_DESTRUCTIVE=true` is set in the plugin's MCP config. This
is deliberate. **Never suggest flipping that flag as a casual fix.** If a user
genuinely needs to remove a property or a sitemap, tell them what the flag does,
let them set it themselves, and confirm the exact target before acting.

## Reading the numbers

**Clicks** — someone clicked through to the site. **Impressions** — a page
appeared in results, whether or not it was scrolled into view. **CTR** —
clicks ÷ impressions. **Position** — average rank; lower is better.

Four things people get wrong, every time:

- **Averaged position is a weak signal.** An "average position 8.4" can be one
  query at 2 and forty at 20. Segment before concluding anything.
- **Branded and non-branded traffic must be separated.** Brand queries convert
  at high CTR and swamp the averages. Report them as two lines, always. If a
  site profile defines brand terms, filter on those; otherwise treat queries
  containing the company or product name as branded.
- **Impressions move for reasons that have nothing to do with the site.** A SERP
  layout change, a new AI overview, or seasonality shifts impressions without
  any ranking change. Check whether position held before blaming the site.
- **Rank ≠ traffic.** A page can climb from 8 to 5 and lose clicks because an
  AI overview or a featured snippet now sits above it.

**CTR benchmarks** (WEB, desktop+mobile blended) — position 1: 25–35%;
2–3: 10–20%; 4–10: 2–8%; 11+: under 2%. Use them as a smell test: a page at
position 3 with 2% CTR has a title/description problem, not a ranking problem.

### The sitelink trap — check this before calling anything an anomaly

A page ranking top-three with near-zero CTR looks like the most dramatic finding
on a site. Usually it is not a finding at all.

When Google shows a brand result, it attaches **sitelinks** — secondary pages
under the main result. Each sitelink is credited with an *impression at
position ~1* for the brand query. The click almost always goes to the main
result. So `/support`, `/pricing`, `/about` and similar pages accumulate
thousands of position-1 impressions and a handful of clicks, purely as a side
effect of the homepage ranking for the brand.

**Before reporting a high-position / low-CTR page as a problem, run
`get_search_by_page_query` on it.** The signature is unmistakable:

```
/why-kugamon   →  query "kugamon"  ·  1,262 impressions  ·  2 clicks  ·  position 1.0
```

One brand query supplying nearly all impressions at position ~1. That is a
sitelink. Report it as working as intended and move on.

A real high-position / low-CTR problem looks different: a **non-branded** query
with meaningful impressions at position 1–3 and a poor CTR. That is either an
intent mismatch (you rank for an image or definition query that will never
convert) or a genuine snippet problem.

This matters beyond the one page. Sitelink impressions inflate site-wide
impression counts and depress site-wide CTR, so an average that includes them
understates real performance.

## Data freshness

`GSC_DATA_STATE=all` (the default) includes fresh, unconfirmed data and matches
what the GSC web dashboard shows. `final` returns only confirmed data, lagging
2–3 days. Two consequences worth stating in any report:

- The **last 2–3 days are always provisional** and will revise upward. Never
  call a dip in the last 48 hours a trend.
- If numbers disagree with the GSC dashboard, check this setting before hunting
  for a bug. `final` vs `all` explains most "the API is wrong" reports.

## Tool limitations that will mislead you

These are not theoretical. Each one produced a wrong finding in real use before
it was written down.

### `sort_by` does nothing. Never trust it.

`get_advanced_search_analytics` accepts `sort_by` and `sort_direction`, and
**silently ignores them.** The server sets an `orderBy` field on the request;
[Google's Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
has no such field, so Google discards it. Results always come back **sorted by
clicks, descending**, whatever you asked for.

Verified two ways: the documented request body has no `orderBy` member, and
requesting `sort_by=position, ascending` returns positions in the order
9.4, 18.6, 12.4, 11.0 — unchanged.

This is worse than an error, because the tool reports the sort it did not
perform. Do not present results as "top by impressions" when you asked for that
sort; you will be describing a clicks-ranked list.

### The consequence: high-impression zero-click queries are invisible

Because sorting is fixed to clicks, a `row_limit` of 100 or 200 returns every
query that has clicks, then fills the remainder with **zero-click queries in
arbitrary order** — in practice alphabetical. The most valuable queries in an
SEO analysis are exactly the ones with many impressions and no clicks, and
those land wherever the alphabet puts them.

A real example: a 200-row pull surfaced a cluster of `apttus*` queries and
missed `conga cpq alternatives` — 500 impressions, position 12.5, zero clicks,
the single largest opportunity on the site. It was invisible because it starts
with C.

**The workaround: filter instead of sort.** Filters *do* work.

```
get_advanced_search_analytics
  dimensions=query
  filter_dimension=query  filter_operator=contains  filter_expression=alternative
```

Run one pull per commercially meaningful term — `alternative`, `competitor`,
`vs`, `pricing`, `migrate`, each competitor's name, each core product term. Each
returns a small, complete slice you can rank yourself. Cover the terms the
business actually cares about rather than hoping they sort to the top.

**Say what you did not see.** A filtered sweep is targeted, not exhaustive: it
cannot surface a valuable query whose wording you did not think to filter for.
State that limitation in the report rather than implying full coverage.

## Workflows

### Site health check
1. `get_performance_overview`, `days=28`.
2. `get_search_analytics`, `dimensions=query`, `row_limit=100` — split branded
   vs non-branded.
3. `get_search_analytics`, `dimensions=page`, `row_limit=25`.
4. `get_sitemaps` — any error or warning is a finding.
5. Report: performance summary, top queries, top pages, sitemap status, and
   three to five specific next actions.

### Keyword opportunity analysis
1. `get_search_analytics`, `dimensions=query`, `row_limit=200` for the queries
   that have clicks — that part of the ranking is reliable.
2. **Then run filtered pulls** for the terms the business cares about, because
   step 1 cannot show you a zero-click query (see "Tool limitations"). Filter on
   each competitor name, plus `alternative`, `competitor`, `vs`, `pricing`,
   `migrate`, and each core product term. This is where the opportunities are.
3. Sort every query into one bucket:
   - **Winners** — position 1–3 with healthy CTR. Protect; don't touch.
   - **Striking distance** — position 4–15 with real impressions. The highest
     return per hour of work on the whole list.
   - **High impressions, low CTR** — ranks fine, snippet doesn't earn the click.
     Rewrite the title tag and meta description.
   - **Off page one** — position 11–20 with volume. Needs content depth or
     internal links, not a snippet tweak.
   - **Long-tail** — low volume, high intent. Cluster into one page rather than
     chasing individually.
4. For anything promising, pull `dimensions=query,page` filtered to that query
   to see which page actually ranks — and whether more than one does. Two
   frequent findings: the *wrong* page ranks for a commercially valuable query,
   and several pages split it between them (see the cannibalization check).
5. If the site profile lists competitors, flag every query containing a
   competitor name — comparison intent is high-value traffic and usually
   under-served. Also report competitors the site earns **no** impressions for;
   an absent competitor is a content gap, and it is invisible unless you look
   for it by name.

### Diagnosing a traffic drop
1. `compare_search_periods` on the affected range vs the equivalent prior range.
2. Decide which of four shapes it is before recommending anything:
   - **Position held, impressions fell** → demand or SERP-layout change, not
     the site's fault. Check seasonality and whether an AI overview appeared.
   - **Position fell, impressions held** → ranking loss. Which queries? Which
     pages? Was there a content change or a Google update on that date?
   - **Impressions held, CTR fell** → the SERP around the result changed, or a
     title got rewritten by Google.
   - **Everything fell off a cliff on one date** → technical. Go straight to
     `gsc-indexing-diagnostics`; suspect deindexing, robots.txt, or a migration.
3. Never attribute a drop to "a Google update" without checking the other three.
   It is the most common wrong answer in SEO reporting.

### Page-level deep dive
1. `get_search_by_page_query` for the page's actual query profile.
2. Compare that against what the page was *written* to target. The gap is the
   finding.
3. `inspect_url_enhanced` to rule out a technical cause.
4. Recommend: retarget the page, split it, or merge it into a stronger one.

### Cannibalization check
Two pages competing for one query costs both of them rank. This is the most
commonly missed diagnosis, because query-only and page-only views both hide it —
you have to pair the dimensions.

1. `get_advanced_search_analytics` with `dimensions=query,page`, filtered to the
   query or term under investigation. The filter matters: an unfiltered pull is
   clicks-sorted, and cannibalized queries usually have zero clicks, which is
   the whole problem.
2. Group by query; flag any query where two or more pages draw impressions.
3. Pick the page that should own it, then consolidate, canonicalize, or
   differentiate the others.

A worked example of the signature:

```
conga cpq alternatives → transition/from-conga                   328 impr, pos 13.2
                       → /conga-cpq                              157 impr, pos 10.8
                       → /resources/cpq-salesforce-cpq-alternatives  15 impr, pos 15.9
```

500 impressions of commercial intent, three pages, zero clicks, none on page
one. Note the third page holds the *best* position on the *least* exposure —
a strong hint about which page Google finds most relevant, and worth weighing
against which page the business wants to win.

### Recognising AI-agent queries
A query that reads as a paragraph — "about me: vp revenue operations… question:
which cpq platforms integrate natively with billing?" — is an AI assistant
searching on a user's behalf, not a person typing. They arrive with 1–10
impressions each and often good positions.

Do not chase them individually and do not treat them as long-tail keywords to
target; the exact wording will never repeat. Report the **cluster** as a
signal: it means the site's comparison and definition content is being consumed
by AI assistants, which is an argument for consolidating that content rather
than fragmenting it. Exclude them from CTR averages — nobody clicks, because
nobody is watching.

## Writing the report

Lead with what changed and what to do, not with a table of everything pulled.
Structure that works:

1. **Headline** — one sentence on the direction of the site.
2. **The numbers** — branded and non-branded on separate lines, with the
   comparison period stated explicitly.
3. **What changed** — the two or three movements that matter.
4. **Recommendations** — specific, ordered by return, each naming the page or
   query it applies to. "Improve the meta descriptions" is not a
   recommendation. "Rewrite the title on /pricing, which sits at position 4 for
   a query with 2,100 impressions and a 1.1% CTR" is.

Say what the data does not cover. GSC has no conversion data, a 16-month
history limit, and omits anonymized low-volume queries — which can be a large
share of the true long tail.

**If the user wants this as a file rather than as chat** — "as a report", "as a
PDF", "something I can send" — hand off to the `gsc-report` skill once the
analysis is done. It renders a print-ready HTML document styled in the site's
own brand. Do the thinking first; that skill only handles presentation.

## Argument reference

- `row_limit` — 20 for a quick look, 200 for analysis, up to 500 on
  `get_search_analytics`. Beyond that use `get_advanced_search_analytics`.
  Note the 500 cap is self-imposed by the server; the API's own limit is 25,000.
- `sort_by` / `sort_direction` — accepted, ignored. Results are always
  clicks-descending. Use filters instead.
- `dimensions` — `query`, `page`, `country`, `device`, `date`, `searchAppearance`.
  Combine with commas.
- Country filters use ISO 3166-1 alpha-3: `usa`, `gbr`, `deu`.
- Device values: `DESKTOP`, `MOBILE`, `TABLET`.
- For one subdomain inside a domain property, use
  `get_advanced_search_analytics` with a page filter — there is no subdomain
  dimension.

## Demo mode

If no GSC property is connected, `sample-data/` in the repo has synthetic
exports seeded with a striking-distance cluster, a high-impression/low-CTR page,
and a cannibalization pair. Run the analysis against those to show the shape of
a report before anyone connects a real property.
