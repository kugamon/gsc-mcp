---
description: Compare two time periods and diagnose what actually caused a traffic change
argument-hint: [site-url] [period, e.g. "last 28 days vs previous 28"]
allowed-tools: ["mcp__*gsc*"]
---

Compare Search Console performance across two periods for $ARGUMENTS and explain
what changed.

Follow the "Diagnosing a traffic drop" workflow in the `gsc-seo-analysis` skill.
The goal is a cause, not a table of deltas.

1. `list_properties` and resolve the exact `site_url`.
2. Read the site profile if one exists — the "Known context" section may already
   explain the change (migration, seasonality, a deliberate noindex).
3. `compare_search_periods` for the two ranges. Default to the last 28 days vs
   the prior 28 unless $ARGUMENTS says otherwise. If a year-over-year view is
   more meaningful for a seasonal business, run both.
4. Classify the change into one of four shapes before recommending anything:
   - **Position held, impressions fell** → demand or SERP-layout change. Not a
     site fault. Check seasonality and whether an AI overview now sits above.
   - **Position fell, impressions held** → ranking loss. Identify which queries
     and pages, and what changed on those dates.
   - **Impressions held, CTR fell** → the SERP around the result changed, or
     Google rewrote the titles.
   - **Everything fell on a single date** → technical. Switch to
     `/indexing-check` and suspect deindexing, robots.txt, or a migration.
5. Drill into the specific losers: `get_search_analytics` on the affected
   queries, and `get_search_by_page_query` on the affected pages.

Do not attribute the change to "a Google algorithm update" unless the other
three shapes have been ruled out and the timing lines up with a confirmed
update. It is the most common wrong answer in SEO reporting.

Report: the headline change with both periods stated, the diagnosis with the
evidence that supports it, the specific queries and pages responsible, and what
to do — including "nothing, this is seasonal" when that is the honest answer.
Note that the most recent 2–3 days are provisional and will revise upward.
