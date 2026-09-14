# Tool reference

The 21 tools exposed by the bundled server, as of vendored version 0.3.3
(commit `b3f2ab8`). If you re-sync the server, re-check this list — see
`plugins/gsc-seo/server/UPSTREAM.md`.

## Orientation

| Tool | Purpose |
| --- | --- |
| `get_capabilities` | Full tool list plus current auth status, in one call. Best first call in any session. |
| `list_properties` | Every property the credential can read, with exact `site_url` strings. Always call before anything site-specific. |
| `get_site_details` | Verification and ownership detail for one property. |

## Search analytics

| Tool | Purpose | Key arguments |
| --- | --- | --- |
| `get_search_analytics` | Top queries / pages / countries / devices | `site_url`, `days`, `dimensions`, `row_limit` (≤500) |
| `get_advanced_search_analytics` | Filtered, sorted, paginated analytics up to 25,000 rows | date range, dimension filters, `search_type` (WEB, IMAGE, VIDEO, NEWS, DISCOVER) |
| `get_performance_overview` | Summary metrics plus daily trend | `site_url`, `days` |
| `compare_search_periods` | Two date ranges side by side with deltas | two ranges |
| `get_search_by_page_query` | Queries driving traffic to one specific page | `site_url`, `page_url` |

`dimensions` accepts `query`, `page`, `country`, `device`, `date`,
`searchAppearance`, comma-separated. Country filters use ISO 3166-1 alpha-3
(`usa`, `gbr`, `deu`). Device values are `DESKTOP`, `MOBILE`, `TABLET`.

There is no subdomain dimension — filter on `page` inside a domain property.

## URL inspection

| Tool | Purpose | Notes |
| --- | --- | --- |
| `inspect_url_enhanced` | Coverage state, last crawl, Google's canonical vs declared, mobile usability, rich results | One URL |
| `batch_url_inspection` | The same for several URLs | Up to 10 per call |
| `check_indexing_issues` | Screen a URL list down to the ones with problems | The right first call for an audit |

Quota: roughly 2,000 inspections/day and 600/minute per property. Requires
**Full** permission on the property — Restricted users cannot inspect URLs.

## Sitemaps

| Tool | Purpose |
| --- | --- |
| `get_sitemaps` | List sitemaps with status |
| `list_sitemaps_enhanced` | Adds type, URL counts, errors, warnings |
| `get_sitemap_details` | Deep inspection of one sitemap |
| `submit_sitemap` | Submit or resubmit |
| `manage_sitemaps` | Combined list / details / submit / delete |
| `delete_sitemap` | Remove a sitemap — **destructive** |

## Authentication

| Tool | Purpose |
| --- | --- |
| `reauthenticate` | Opens a browser OAuth login. OAuth path only; irrelevant to service accounts. |
| `get_creator_info` | Upstream author attribution. |

## Destructive — off by default

These refuse to run unless `GSC_ALLOW_DESTRUCTIVE=true`:

| Tool | Effect |
| --- | --- |
| `add_site` | Adds a property to the Search Console account |
| `delete_site` | Removes a property — **its history is not recoverable** |
| `delete_sitemap` / `manage_sitemaps` delete | Removes a sitemap submission and its history |

The default is off on purpose. Enable it for a single intended operation and
turn it back off; do not leave it on.

## What no tool here can do

- **Request indexing for a URL.** UI-only in Search Console; no API exposes it.
- **Submit to Google via IndexNow.** Google does not participate — Bing,
  Yandex, Seznam, and Naver do.
- **Read more than 16 months of history.** Search Console does not retain it.
- **See anonymized low-volume queries.** Withheld for privacy, so query-level
  clicks never sum to the site total.
- **Report conversions.** GSC has clicks, not outcomes.
