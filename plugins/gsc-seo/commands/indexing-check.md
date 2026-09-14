---
description: Audit URL indexing status and diagnose why pages are not indexed
argument-hint: [site-url] [optional: specific URLs, comma-separated]
allowed-tools: ["mcp__*gsc*"]
---

Audit indexing for $ARGUMENTS.

Use the `gsc-indexing-diagnostics` skill — in particular the status table and
the outside-in order of operations.

1. `list_properties` and resolve the exact `site_url`.
2. Build the URL list:
   - If $ARGUMENTS named specific URLs, use those.
   - Otherwise `get_search_analytics`, `dimensions=page`, `row_limit=100` for
     the pages Google already knows about, and ask the user for any important
     pages missing from that list — pages with zero impressions are exactly the
     ones most likely to have a problem, and they will not appear here.
3. Check the site level before the page level: `get_sitemaps` for fetch errors.
   A sitemap that Google cannot read explains missing pages faster than
   inspecting them one at a time.
4. `check_indexing_issues` across the URL list to filter down to problems.
5. `inspect_url_enhanced` on each flagged URL, plus any page the user named as
   important regardless of flag status.
6. Respect the inspection quota (~2,000/day, 600/minute per property). On a
   large site, inspect priority pages plus a sample — say that you sampled.

Report in three groups, never one undifferentiated list:

- **Broken** — needs a fix. Give the specific cause and the specific action.
- **Working as intended** — noindex, canonicalized, redirects. Confirm and move on.
- **Judgment calls** — "Crawled – currently not indexed" and
  "Discovered – currently not indexed". Explain that these are quality and
  crawl-priority signals, not technical faults, and that resubmission will not
  change them.

Order by the page's commercial value, not by Search Console's severity label.
For each broken item, state whether the fix is in the CMS, the server, the
robots.txt, or the content.
