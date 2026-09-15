---
name: gsc-site-profile
plugin: gsc-seo
version: 1.0.1
description: >
  Create or update the site profile that makes SEO reports specific to one
  business instead of generic. Use when the user says "set up my site profile",
  "configure gsc-seo for my site", "the reports are too generic", "teach it
  about our keywords", "add our competitors", "which pages should it prioritize",
  or when a GSC analysis is being run for a site that has no profile yet.
---

# Site profile

A site profile is a short Markdown file describing one site: its brand terms,
what it sells, who it competes with, and which pages matter. The analysis skills
read it so that a report says "the /pricing page is losing ground on a
competitor-comparison query" instead of "some pages changed position".

Everything works without a profile. A profile is what raises the output from
correct to useful.

## Where it lives

The profile belongs **with the user's own files, not in this plugin**. Plugin
directories are replaced wholesale on update, so anything stored inside one is
lost at the next version bump. Recommend, in order:

1. The repo or working folder for the site itself — `docs/seo-profile.md`.
   Best option: it is versioned alongside the thing it describes.
2. The user's Claude project or workspace folder.
3. Anywhere stable the user will remember, as long as they can point Claude at it.

Ask the user where to put it rather than choosing for them. Then tell them to
mention the path when they ask for analysis, or keep it in a folder Claude
already has access to.

A profile is **business-sensitive**. Competitor targeting and page priorities
are strategy. Do not commit one to a public repository, and do not paste one
into a shared document without asking.

## Building one

Do not interview the user through all of this. Fill in what can be derived and
confirm the rest.

**Derive first:**
- `list_properties` → the exact `site_url`.
- `get_search_analytics` with `dimensions=query`, `row_limit=200` → the queries
  that already bring traffic. Brand terms are usually the highest-CTR cluster.
- `get_search_analytics` with `dimensions=page`, `row_limit=50` → the pages that
  already earn traffic.
- Fetch the homepage to learn what the company actually says it does.

**Then ask, in one pass, only what cannot be derived:**
- Which pages matter commercially, as opposed to which get traffic today? These
  are frequently different, and the gap is often the most valuable finding in
  the first report.
- Who do you compete with — the names a buyer would search alongside yours?
- Is there a keyword you want to win that you do not rank for at all?

## Template

```markdown
# SEO profile — <company>

**GSC property:** sc-domain:example.com
**What the company sells:** <one sentence a stranger would understand>
**Primary audience:** <who buys>

## Brand terms
Queries containing these count as branded and are reported separately:
- example, example.com, <product names>, <common misspellings>

## Keyword categories
Sort queries into these buckets when reporting:
1. **Branded** — see above
2. **Core product** — <the two or three things you actually sell>
3. **Category / educational** — <what buyers search before they know you exist>
4. **Competitor comparison** — any query naming a competitor
5. **Off-target** — traffic that will never convert; exclude from CTR averages

## Competitors
Flag any query containing these names as competitor-comparison intent:
- <competitor>, <competitor>, <competitor>

## Priority pages
Ordered by commercial value, highest first:
| Page | Purpose | Target query |
| --- | --- | --- |
| /pricing | Conversion | <primary query> |
| /product/<x> | Product | <primary query> |
| /compare/<competitor> | Comparison | <competitor> alternative |

## Known context
- <site migration dates, redesigns, or anything that explains a step change>
- <seasonality>
- <deliberate exclusions — pages that are noindexed on purpose>
```

## Keeping it honest

- **"Known context" is the section that pays for itself.** A migration date or
  a seasonal pattern recorded here stops the next traffic-drop analysis from
  blaming a Google update.
- Revisit it when the site relaunches, the product line changes, or a competitor
  is acquired or renamed — a stale competitor list quietly produces confident,
  wrong findings.
- Keep it to one page. A profile nobody maintains is worse than none, because
  it is trusted and wrong.
