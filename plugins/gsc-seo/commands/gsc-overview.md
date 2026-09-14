---
description: Full SEO overview from Google Search Console — performance, keywords, pages, sitemaps, quick wins
argument-hint: [site-url or property name] [days, default 28]
allowed-tools: ["mcp__*gsc*"]
---

Produce a Search Console overview for $ARGUMENTS.

Use the `gsc-seo-analysis` skill for interpretation rules — especially the
branded/non-branded split and the CTR benchmarks.

1. `get_capabilities` to confirm authentication. If it reports not
   authenticated, stop and run `/gsc-doctor` instead of failing tool by tool.
2. `list_properties`. If $ARGUMENTS named a site, match it to an exact
   `site_url`. If not, and there is more than one property, ask which.
3. If the user has a site profile, read it before analyzing.
4. Pull, in this order:
   - `get_performance_overview` — default 28 days unless $ARGUMENTS says otherwise
   - `get_search_analytics`, `dimensions=query`, `row_limit=100`
   - `get_search_analytics`, `dimensions=page`, `row_limit=25`
   - `get_sitemaps`
5. Report:
   - **Headline** — one sentence on direction, with the period stated.
   - **Performance** — clicks, impressions, CTR, average position, branded and
     non-branded on separate lines.
   - **Top queries** and **top pages** — ten each, with metrics.
   - **Sitemap status** — only if something is wrong; say "all healthy" otherwise.
   - **Quick wins** — striking-distance queries (position 4–15) and
     high-impression/low-CTR pages, each naming the specific page or query.
6. Close with three to five recommendations ordered by expected return. Each
   must name a page or query. No generic advice.

Flag the last 2–3 days as provisional if the trend depends on them.
