---
description: Keyword performance report with opportunity buckets — winners, striking distance, low CTR, long tail
argument-hint: [site-url or property name] [days, default 28]
allowed-tools: ["mcp__*gsc*"]
---

Build a keyword opportunity report for $ARGUMENTS.

Follow the "Keyword opportunity analysis" workflow in the `gsc-seo-analysis`
skill.

1. `list_properties` and resolve the exact `site_url` (ask if ambiguous).
2. Read the site profile if one exists — it supplies brand terms, keyword
   categories, and competitor names.
3. `get_search_analytics`, `dimensions=query`, `row_limit=200`, default 28 days.
4. Separate branded from non-branded first. Report branded as a single summary
   line and then set it aside — it is not where the opportunity is.
5. Sort the non-branded queries into buckets:
   - **Winners** (position 1–3, healthy CTR) — protect
   - **Striking distance** (position 4–15, real impressions) — highest return
   - **High impressions, low CTR** — snippet problem, not a ranking problem
   - **Off page one** (position 11–20, volume) — needs depth or internal links
   - **Long tail** — cluster rather than chase individually
6. For the top five opportunities, run `get_search_by_page_query` to identify
   which page currently ranks. Call out any case where the wrong page ranks for
   a commercially valuable query.
7. If the profile lists competitors, add a **competitor comparison** section
   covering every query containing a competitor name, plus competitor names the
   site earns no impressions for at all.

Output a table per bucket (query, clicks, impressions, CTR, position, ranking
page) and then a prioritized action list. Say which action you would do first
and why.
