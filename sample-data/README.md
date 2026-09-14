# Sample data

Synthetic Search Console exports for a fictional company, Northwind Analytics.
Use these to see what the skills produce before connecting a real property — no
Google account, no credentials, no setup.

**None of this is real data.** The domain is `.example`, which is reserved and
resolves nowhere.

| File | Stands in for |
| --- | --- |
| `queries-28d.csv` | `get_search_analytics` with `dimensions=query` |
| `pages-28d.csv` | `get_search_analytics` with `dimensions=page` |
| `query-page-pairs-28d.csv` | `get_advanced_search_analytics` with `dimensions=query,page` |
| `url-inspection.csv` | `check_indexing_issues` / `batch_url_inspection` |

Pair them with `plugins/gsc-seo/profiles/example-profile.md`, which is the site
profile for the same fictional company.

## Try it

> Analyze `sample-data/queries-28d.csv` and `sample-data/pages-28d.csv` using
> the gsc-seo-analysis skill and the example profile. Give me a keyword
> opportunity report.

> Using `sample-data/query-page-pairs-28d.csv`, find any keyword cannibalization
> and tell me which page should own each query.

> Read `sample-data/url-inspection.csv` and give me an indexing audit — separate
> what is actually broken from what is working as intended.

## What is deliberately planted

Each file hides findings a real audit should surface. Worth knowing so you can
judge whether the output is any good:

- **A striking-distance cluster.** `self serve bi tool`, `no code reporting
  tool`, and `warehouse dashboard tool` all sit at position 7–9 with 1,800–3,000
  impressions. Highest return on the list.
- **A high-impression, low-CTR page.** `/guides/kpi-dashboard` takes 20,600
  impressions at position 5.8 and converts 0.57% of them. A snippet problem, not
  a ranking problem.
- **A cannibalization pair.** `/guides/kpi-dashboard` and
  `/blog/kpi-dashboard-examples` both draw impressions for *both*
  `how to build a kpi dashboard` and `kpi dashboard examples`, splitting each.
  The inspection file confirms it: Google has already chosen the guide as
  canonical for the blog post.
- **Brand ambiguity inflating the numbers.** `northwind database sample` and
  friends bring 43,000 impressions at position 42+ and essentially zero clicks —
  people looking for the SQL Server sample database. Any CTR average that
  includes them is meaningless. A good report excludes them and says why.
- **Competitor gaps.** The profile lists five competitors; the data shows
  impressions for Metabase, Looker, Mode, and Omni — and nothing at all for
  Lightdash. The `/compare/lightdash` page is "Discovered – currently not
  indexed", which explains it.
- **A genuine technical fault, buried in noise.**
  `/integrations/bigquery` returns a 5xx. It sits in a list where most entries
  are noindex, redirects, and robots-blocked pages that are all working as
  intended. A report that lists twelve "issues" undifferentiated has failed;
  the 5xx and the soft 404 on `/careers` are the only two that need action.
