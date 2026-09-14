---
description: Check sitemap submission, fetch status, and diagnose "Couldn't fetch" errors
argument-hint: [site-url]
allowed-tools: ["mcp__*gsc*"]
---

Check sitemap health for $ARGUMENTS.

Use the "Sitemap 'Couldn't fetch'" section of the `gsc-indexing-diagnostics`
skill.

1. `list_properties` and resolve the exact `site_url`.
2. `list_sitemaps_enhanced` for every sitemap with its type, URL count, errors,
   warnings, and last-read date.
3. `get_sitemap_details` on any sitemap showing an error or a stale last-read.

For each problem sitemap, work the checklist rather than guessing:

- Does the submitted URL return 200 with an XML content type? Verify it — do not
  assume from the fact that it loads in a browser.
- Does the submitted URL redirect? Protocol or host mismatches between the
  submitted string and the live URL are the most common cause of
  "Couldn't fetch".
- Is robots.txt reachable, returning 200, and not blocking the sitemap path?
- Is a CDN, worker, or Vary rule serving Googlebot something different from a
  browser?
- How long ago was it submitted? A new sitemap can read as "Couldn't fetch" for
  hours or days before the first successful fetch.

If the fetch checks all pass, say so plainly: the configuration is correct and
the status is lagging. Do not invent a fix for a sitemap that is working.

Do **not** offer to delete and resubmit as a first move — it discards submission
history, requires `GSC_ALLOW_DESTRUCTIVE=true`, and fixes nothing that
resubmitting the same URL would not.

Close with: last successful read per sitemap, discovered vs indexed URL counts
where available, and any coverage gap between what the sitemap lists and what
Search Console reports as indexed.
