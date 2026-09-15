---
name: gsc-seo-analysis
plugin: gsc-seo
version: 1.1.0
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
| `get_advanced_search_analytics` | Same, with filters, sorting, pagination | Up to 25,000 rows. Search types: WEB, IMAGE, VIDEO, NEWS, DISCOVER. |
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

## Data freshness

`GSC_DATA_STATE=all` (the default) includes fresh, unconfirmed data and matches
what the GSC web dashboard shows. `final` returns only confirmed data, lagging
2–3 days. Two consequences worth stating in any report:

- The **last 2–3 days are always provisional** and will revise upward. Never
  call a dip in the last 48 hours a trend.
- If numbers disagree with the GSC dashboard, check this setting before hunting
  for a bug. `final` vs `all` explains most "the API is wrong" reports.

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
1. `get_search_analytics`, `dimensions=query`, `row_limit=200`, `days=28`.
2. Sort every query into one bucket:
   - **Winners** — position 1–3 with healthy CTR. Protect; don't touch.
   - **Striking distance** — position 4–15 with real impressions. The highest
     return per hour of work on the whole list.
   - **High impressions, low CTR** — ranks fine, snippet doesn't earn the click.
     Rewrite the title tag and meta description.
   - **Off page one** — position 11–20 with volume. Needs content depth or
     internal links, not a snippet tweak.
   - **Long-tail** — low volume, high intent. Cluster into one page rather than
     chasing individually.
3. For anything promising, run `get_search_by_page_query` to see which page
   actually ranks. A frequent finding: the *wrong* page ranks for a
   commercially valuable query, and the fix is internal linking, not new content.
4. If the site profile lists competitors, flag every query containing a
   competitor name — comparison intent is high-value traffic and usually
   under-served.

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
Two pages competing for one query costs both of them rank.
1. `get_advanced_search_analytics` with `dimensions=query,page`.
2. Group by query; flag any query where two or more pages draw impressions.
3. For each: pick the page that should own the query, and recommend
   consolidating, canonicalizing, or differentiating the other.

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
