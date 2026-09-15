---
name: gsc-site-profile
plugin: gsc-seo
version: 1.3.0
description: >
  Create or update the site profile that makes SEO reports specific to one
  business instead of generic. Use when the user says "set up my site profile",
  "configure gsc-seo for my site", "the reports are too generic", "teach it
  about our keywords", "add our competitors", "which pages should it prioritize",
  or when a GSC analysis is being run for a site that has no profile yet. Also
  covers extracting the site's brand tokens — fonts, colours, webfont
  stylesheet — from the live site, which is what lets gsc-report style documents
  in the company's own design; use it when the user asks to "match our branding",
  "use our fonts and colours", or reports that a document looks generic.
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

## Brand tokens
Used by the gsc-report skill to style documents in the site's own design.
Extracted from the live site; see "Extracting brand tokens" below.

| Token | Value |
| --- | --- |
| Font stylesheet | <public webfont CSS URL, or "none"> |
| Heading font | <computed font-family of h1> |
| Body font | <computed font-family of body> |
| Dark / headings | #______ |
| Accent / links / CTA | #______ |
| Body text | #______ |
| Page background | #______ |
| Border | #______ |

Extracted <date> from <url>.
```

## Extracting brand tokens

Run this once per site. The result is cached in the profile, so reports after
the first cost nothing.

**Read computed styles from the live site, don't parse the CSS.** Parsing
stylesheets means resolving custom properties, framework classes and cascade
order by hand, and then guessing which of forty declared colours is the brand
one. `getComputedStyle` has already done all of that — it reports what actually
rendered.

Open the site's homepage in a browser and run:

```js
(() => {
  const hex = v => {
    if (!v || !v.startsWith('rgb')) return v;
    const n = v.match(/\d+(\.\d+)?/g).map(Number);
    if (n.length >= 4 && n[3] === 0) return 'transparent';
    return '#' + n.slice(0,3).map(x => x.toString(16).padStart(2,'0')).join('');
  };
  const cs = s => { const e = document.querySelector(s); return e ? getComputedStyle(e) : null; };
  const body = cs('body'), h1 = cs('h1') || cs('h2'), a = cs('a[href]');

  // Area-weighted colour census: which colours the page is actually made of,
  // not which colours appear somewhere in the stylesheet.
  const census = {};
  [...document.querySelectorAll('*')].slice(0, 3000).forEach(e => {
    const s = getComputedStyle(e), r = e.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return;
    if (s.backgroundColor && s.backgroundColor !== 'rgba(0, 0, 0, 0)') {
      const h = hex(s.backgroundColor);
      census[h] = (census[h] || 0) + Math.round(r.width * r.height / 1000);
    }
  });

  return {
    fontStylesheets: [...document.querySelectorAll('link[rel="stylesheet"]')]
      .map(l => l.href).filter(h => /typekit|fonts\.googleapis|fonts\.net|cloud\.typography/i.test(h)),
    headingFont: h1 && h1.fontFamily,
    bodyFont: body.fontFamily,
    headingColor: h1 && hex(h1.color),
    linkColor: a && hex(a.color),
    bodyText: hex(body.color),
    pageBg: hex(body.backgroundColor),
    topColours: Object.entries(census).sort((x, y) => y[1] - x[1]).slice(0, 8)
  };
})()
```

Reading the result:

- **`topColours` is ranked by painted area**, so the page background lands
  first, the brand's dark band second, and the CTA colour third. That ordering
  is the point — it separates the two or three colours the site is built from
  out of the dozens it declares.
- **`headingColor` is usually the dark token**, `linkColor` usually the accent.
  Check them against `topColours`; when they agree, you have it.
- **The font stylesheet matters more than the font name.** A heading font of
  `itc-avant-garde-gothic-pro` is worthless in a standalone file unless the
  Typekit or Google Fonts CSS URL comes with it. If there is no public
  stylesheet URL, record the family anyway and let the fallback stack carry it —
  do not substitute a lookalike font and call it the brand.
- Grab the border colour from any hairline the site uses; `#e5e5e5`-ish neutrals
  are typical and a sensible default if none is found.

Confirm the palette with the user before saving it. Extraction gets the dark and
accent right most of the time, and "most of the time" is not good enough for
something going to a client.

## Keeping it honest

- **"Known context" is the section that pays for itself.** A migration date or
  a seasonal pattern recorded here stops the next traffic-drop analysis from
  blaming a Google update.
- Revisit it when the site relaunches, the product line changes, or a competitor
  is acquired or renamed — a stale competitor list quietly produces confident,
  wrong findings.
- Keep it to one page. A profile nobody maintains is worse than none, because
  it is trusted and wrong.
