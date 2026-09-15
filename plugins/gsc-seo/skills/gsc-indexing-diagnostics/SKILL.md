---
name: gsc-indexing-diagnostics
plugin: gsc-seo
version: 1.2.0
description: >
  Diagnose indexing, crawling, and sitemap problems in Google Search Console.
  Use when the user says a page "isn't showing up in Google", "isn't indexed",
  asks to "audit indexing", "check if these URLs are indexed", or reports a
  sitemap error — especially "Couldn't fetch", "Sitemap could not be read",
  "Discovered – currently not indexed", "Crawled – currently not indexed",
  "blocked by robots.txt", "noindex", canonical problems, or a new site or page
  that Google has not picked up. Also covers getting new URLs crawled faster
  (sitemap resubmission, IndexNow) and what Search Console will and will not
  tell you.
---

# Indexing, crawl, and sitemap diagnostics

Search Console's indexing messages are terse and several of them are routinely
misread. This skill maps each message to what it actually means and what to do.

## Order of operations

Work outside in. Most wasted time in indexing debugging comes from fixing a page
when the problem is at the site level.

1. **Site level** — is the property verified, is robots.txt reachable and
   permissive, is the sitemap being fetched?
2. **Sitemap level** — is it valid, does it contain the URL, is it fresh?
3. **Page level** — `inspect_url_enhanced` on the specific URL.

Only step 3 needs the URL inspection tools. Steps 1 and 2 explain most cases.

## Sitemap "Couldn't fetch"

The most common and most misdiagnosed message. It means Google's fetch of the
sitemap URL did not return a usable response. It does **not** mean the sitemap
is malformed — Google never got far enough to parse it.

Check in this order:

1. **Fetch it yourself, exactly as submitted.**
   `curl -sSI https://example.com/sitemap.xml` — confirm `200` and a
   `Content-Type` of `application/xml` or `text/xml`. An HTML error page served
   with a 200 is a frequent culprit.
2. **Protocol and host must match the submitted string.** A sitemap submitted
   as `http://` that 301s to `https://`, or `example.com` redirecting to
   `www.example.com`, produces this error. Submit the final URL, not the
   redirecting one.
3. **robots.txt must not block it,** and must itself return 200. A robots.txt
   that 404s is fine; one that 500s causes Google to pause crawling entirely.
4. **Check for a Vary or caching layer serving Googlebot something different.**
   If the site is behind a CDN or worker, verify the response with a Googlebot
   user agent, not just a browser one.
5. **Give it time.** A freshly submitted sitemap can display "Couldn't fetch"
   for hours to days before the first successful read, even when everything is
   correct. Re-submitting repeatedly does not speed this up. If `curl` returns
   a clean 200 XML and robots.txt allows it, the configuration is right and the
   status is stale — say so rather than inventing a fix.

Tools: `get_sitemap_details` for the submitted URL's own record,
`list_sitemaps_enhanced` for errors and warnings across all of them.

**Never delete and resubmit a sitemap as a first move.** It discards the
submission history, needs `GSC_ALLOW_DESTRUCTIVE=true`, and fixes nothing that
resubmission over the same URL would not.

## Page-level statuses, decoded

| Status | What it means | What to do |
| --- | --- | --- |
| **Submitted and indexed** | Healthy. | Nothing. |
| **Discovered – currently not indexed** | Google knows the URL exists but has not crawled it. Usually a crawl-budget or perceived-quality signal. | Add internal links from indexed pages. Thin or templated pages often sit here permanently. Resubmitting does not help. |
| **Crawled – currently not indexed** | Google fetched it and chose not to index it. A quality judgment. | This is a content problem, not a technical one. Improve depth and distinctiveness, or accept it. The single most over-"fixed" status in SEO. |
| **Duplicate, Google chose different canonical** | Google disagrees with the declared canonical. | Check the `rel=canonical`, internal links, and sitemap for conflicting signals. Align them. |
| **Alternate page with proper canonical tag** | Working as intended. | Nothing. |
| **Excluded by 'noindex' tag** | A meta robots or X-Robots-Tag header says no. | Intentional? Done. If not, find the tag — often a stray CMS or staging setting. |
| **Blocked by robots.txt** | Crawl disallowed. | Note the trap below. |
| **Soft 404** | Returns 200 but looks like an error or empty page. | Return a real 404, or add content. |
| **Page with redirect** | Not indexable by design. | Confirm the target is the canonical and is itself indexed. |
| **Server error (5xx)** | Fetch failed. | Fix the server, then request indexing. |

### The robots.txt trap

`Disallow` prevents *crawling*, not *indexing*. A blocked URL with external
links can still appear in results as a bare title with no description. Worse:
if a page is blocked by robots.txt, Google cannot see its `noindex` tag — so
blocking a page you want removed does the opposite of what is intended.

To remove a page from the index: allow crawling and serve `noindex`. To keep it
out of the crawl and the index: `noindex` first, wait for it to drop, then
disallow.

## URL inspection

- `inspect_url_enhanced` — one URL, full detail: coverage state, last crawl,
  canonical (Google's vs declared), mobile usability, rich results.
- `batch_url_inspection` — up to 10 URLs.
- `check_indexing_issues` — a list of URLs, filtered to the ones with problems.
  The right first call for an audit.

The inspection API is **quota limited** (roughly 2,000 calls/day and 600/minute
per property). For a large site do not inspect everything. Pull the page list
from `get_search_analytics` with `dimensions=page`, then inspect the priority
pages plus a sample of the rest.

Two details worth reporting accurately:

- **Google's canonical vs the declared canonical.** When they differ, that is
  the finding — the page is being folded into another.
- **Last crawl date.** A priority page not crawled in months is a different
  problem from one crawled yesterday and not indexed.

## Getting new URLs crawled faster

Ranked by what actually works:

1. **Internal links from already-indexed pages.** By a wide margin the most
   effective, and the most neglected. A new page linked from the homepage is
   found in hours.
2. **A fresh, valid sitemap with accurate `lastmod`.** Lying in `lastmod`
   teaches Google to ignore it — only update it when content actually changed.
3. **"Request indexing" in the Search Console UI.** Manual, roughly a dozen a
   day. Not exposed by this MCP server or by any Google API; there is no way to
   automate it, and claiming otherwise is wrong.
4. **IndexNow** — a ping protocol that submits changed URLs to participating
   engines. **Bing, Yandex, Seznam, and Naver participate. Google does not.**
   It is worth doing for Bing coverage, which increasingly feeds AI assistants,
   but it will not get a page into Google. Never present IndexNow as a Google
   indexing method.

There is no paid or API path to faster Google indexing. The Indexing API is
restricted to job postings and livestream structured data; using it for general
pages is outside its terms and does not work.

## Migration and launch checklist

When a site has just moved or launched, check these before diagnosing anything
page by page:

- Property verified for the **new** host and protocol, and a domain property
  added if subdomains matter.
- robots.txt on the new host reachable, 200, and not a leftover
  `Disallow: /` from staging. This one failure mode accounts for a remarkable
  share of "we launched and disappeared from Google".
- No site-wide `noindex` carried over from staging.
- Old URLs 301 to the new ones, one hop, no chains.
- New sitemap submitted, old one left in place until the redirects are picked up.
- Canonical tags point at the new host.

## Reporting findings

Separate **broken** from **working as intended** from **a judgment call**. A
list of forty "issues" where thirty-five are correctly excluded pages is noise
and erodes trust in the audit. Prioritize by the page's commercial value, not
by the severity label Search Console attaches — a "Crawled – currently not
indexed" on a key landing page outranks a hundred excluded tag archives.
