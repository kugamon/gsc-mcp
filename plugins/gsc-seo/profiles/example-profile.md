# SEO profile — Northwind Analytics (EXAMPLE)

> This is a fictional worked example, shipped so you can see the shape of a
> filled-in profile. Copy it, replace everything, and store your real profile
> outside this plugin directory — see the `gsc-site-profile` skill for why.

**GSC property:** sc-domain:northwind-analytics.example
**What the company sells:** A dashboard tool that connects to a warehouse and
gives non-analysts self-serve reporting.
**Primary audience:** Operations and finance managers at 50–500 person
companies, usually without a dedicated analyst.

## Brand terms
- northwind, northwind analytics, northwindanalytics, north wind analytics

## Keyword categories
1. **Branded** — see above
2. **Core product** — self-serve BI, warehouse dashboard, no-code reporting
3. **Category / educational** — "what is a semantic layer", "how to build a KPI
   dashboard", "reverse ETL vs BI"
4. **Competitor comparison** — any query naming a competitor below
5. **Off-target** — "wind analytics", "northwind database sample" (the SQL
   Server sample database — a permanent source of irrelevant impressions;
   exclude from CTR averages)

## Competitors
- Metabase, Looker, Mode, Omni, Lightdash

## Priority pages
| Page | Purpose | Target query |
| --- | --- | --- |
| /pricing | Conversion | northwind analytics pricing |
| /product/dashboards | Product | self serve bi tool |
| /compare/metabase | Comparison | metabase alternative |
| /compare/looker | Comparison | looker alternative for small teams |
| /guides/kpi-dashboard | Top of funnel | how to build a kpi dashboard |

## Known context
- Site moved from `www.` to a domain property on 2026-03-14. Any step change
  in that week is the migration, not a ranking event.
- Q4 is seasonally strong — finance buyers plan budgets in October and November.
- `/docs/*` is intentionally `noindex`; do not report those as indexing errors.
- The "northwind" brand collides with a well-known SQL sample database, so
  branded impressions are inflated and branded CTR runs low. Judge branded
  performance on clicks, not CTR.
