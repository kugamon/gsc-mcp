---
name: gsc-report
plugin: gsc-seo
version: 1.1.0
description: >
  Render a Search Console analysis as a designed, print-ready HTML document
  styled in the site's own brand. Use when the user asks for the analysis "as a
  report", "as a document", "as a PDF", "something I can send", "make it
  pretty", "with charts", "a deck for the team", "export this", "save this
  report", or otherwise wants the output as a file rather than as chat. Also use
  when a recurring or scheduled SEO report is being produced. Do the analysis
  first with gsc-seo-analysis or gsc-indexing-diagnostics; this skill only
  handles turning findings into the document.
---

# Rendering a report

Chat is the right medium for most answers. This skill is for the times it isn't:
something to send a client, attach to a board pack, or keep as a record.

**Analysis first, rendering second.** Never pull data straight into the
template. Work the findings out with `gsc-seo-analysis` or
`gsc-indexing-diagnostics`, decide what matters, and only then render. A
beautifully typeset report that averages branded and non-branded CTR together is
still wrong.

## What to produce

One self-contained HTML file, written to the user's folder, built from
`assets/report-template.html` in this plugin.

It is designed so **Cmd-P → Save as PDF** produces a proper document — A4 page
box, repeating table headers, no card or chart split across a page break. That
is deliberately the whole PDF story: no headless Chromium, no WeasyPrint, no
rendering dependency in the launcher that can break on someone's machine six
months from now.

Tell the user both things when you hand the file over: open it in a browser, and
print to PDF if they need to send it.

## Brand

Read the brand tokens from the site profile and paste them into the `:root`
block. That is the only block that changes between sites.

If the profile has no brand tokens, extract them first — the procedure is in the
`gsc-site-profile` skill. It takes one browser call and is cached afterwards.
If the site cannot be reached, fall back to the neutral defaults below and say
plainly in your reply that the report is unbranded and why.

```css
--font-heading: Georgia, "Times New Roman", serif;
--font-body:    -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
--brand-dark:   #1f2a37;
--brand-accent: #2563eb;
--text:         #1f2937;
--page-bg:      #ffffff;
--border:       #e5e7eb;
```

Never invent a brand colour. An honest neutral report beats a confidently
wrong-coloured one — a client notices the wrong blue immediately.

## Charts

The template uses **inline SVG only**, with hover interactivity added by a small
inline script. There is no charting library and no CDN.

This is not a limitation, it is the design:

- It renders identically on screen, in print, in an emailed file, and offline.
- A report containing a client's traffic data does not phone out to a third
  party to draw a bar.
- There is one copy of the numbers, so a chart cannot disagree with the table
  beside it.
- Nothing to keep in sync, nothing to break when a CDN version is pulled.

Compute the geometry yourself and write real coordinates into the SVG. The
template documents the arithmetic above each chart block:

- **Bar chart** — label gutter 0–165, plot 175–575, `width = value / max * 400`,
  row pitch 26px, `viewBox` height `rows * 26 + 10`.
- **Trend line** — plot x 40–590, y 20–150,
  `x = 40 + i/(n-1) * 550`, `y = 150 - value/max * 130`.

Give every bar and point a `data-tip="Label|Detail"` so it gets a tooltip.

**Chart honestly.** Start bars at zero. Don't truncate an axis to make a change
look dramatic. If two series have different units, don't put them on one axis.

## Choosing what to show

A report that renders every number is a data dump with better typography. Aim
for roughly:

- **4 KPI cards** — the numbers that answer "how are we doing". For a
  performance report: total clicks, non-branded clicks, non-branded CTR, average
  position. Use `data-tone` to colour them against expectation, not against zero.
- **1–2 charts** — one comparison (top pages or queries), one trend if the
  period is long enough to have a shape.
- **2–3 tables** — ten rows each at most. More than that belongs in a CSV.
- **1–2 callouts** — the findings someone would otherwise miss.
- **3–5 recommendations** — each naming a specific page or query.

Colour carries meaning here. `good` / `warn` / `bad` tones on KPIs, pills and
callouts should reflect the reading, so someone scanning the page in ten seconds
gets the right impression. Don't decorate with them.

## Non-negotiables

- **State the period and the property** in the masthead, every time.
- **Branded and non-branded on separate lines.** The single most common way an
  SEO report misleads.
- **Carry the caveats into the footer**, not just into chat — provisional recent
  days, sampled or alphabetically-truncated query pulls, a property whose data
  starts later than the requested window. The file outlives the conversation
  that produced it, and whoever reads it next will not have seen your chat.
- **Never invent a number to fill a slot.** Drop the card or the chart instead.

## Filing it

Write to the user's working folder with a dated, sortable name:

```
gsc-report-<property>-<YYYY-MM-DD>.html
```

for example `gsc-report-example-com-2026-09-14.html`. Present the file so they
can open it. Don't paste the whole report back into chat as well — give the
headline and the two or three findings that matter, and let the document carry
the detail.
