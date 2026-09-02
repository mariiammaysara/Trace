# TRACE Brand Mark

Full rationale, scale test, and application mockups: see the identity deck
(published as an Artifact during this session — ask for the link if you
don't have it).

This directory holds the production assets. It is a standalone brand
folder, deliberately outside `dashboard/` — nothing here is wired into the
app; swapping it in (`dashboard/public/*.svg`) is a separate, deliberate
step for whoever approves the direction.

## The mark

Two nodes on one 45° vector: an open ring (an object's last known position)
connected to a solid dot (its current, confirmed position). Built on a
`0 0 64 64` viewBox — every file below shares that exact geometry, just
recolored or recomposed, so the mark never looks like a different symbol
at a different size.

## Files

| File | Use |
|---|---|
| `favicon.svg` | Browser tab icon. Auto-switches for `prefers-color-scheme` (dark/light browser chrome) via an embedded media query — no separate dark file needed for this one. |
| `symbol-color.svg` | Symbol only, ink + signal cyan, for light backgrounds. |
| `symbol-color-on-dark.svg` | Symbol only, slate + signal cyan, for dark backgrounds. |
| `symbol-mono-black.svg` / `symbol-mono-white.svg` | Strict single-color versions — print, watermarks, anywhere color isn't available. |
| `lockup-horizontal.svg` / `lockup-horizontal-on-dark.svg` | Symbol + wordmark side by side. Navbar, README, site header. |
| `lockup-stacked.svg` / `lockup-stacked-on-dark.svg` | Symbol above, wordmark centered below. Splash/cover use. |

## Wordmark font

Set in **Geist**, weight ~650–700, +0.02em tracking, caps only — the same
family already running the TRACE product UI (`@fontsource-variable/geist`),
so the mark and the product read as one identity rather than two
"on-brand" fonts that don't actually match.

The four `lockup-*.svg` files reference `Geist` with a system-sans
fallback rather than embedding it, so they render correctly wherever Geist
is already available (e.g. pulled directly into the dashboard) and degrade
gracefully to a generic bold sans elsewhere. **Before using a lockup file
outside a Geist-aware context** (a deck, a partner's site, a print vendor),
outline the text to paths first — Illustrator/Figma "Create Outlines," or
an automated tool — so it renders identically everywhere, independent of
whether the viewer has the font.

## Color

| Name | Hex | Role |
|---|---|---|
| Ink | `#0B1220` | Dark ground; mark/wordmark on light. |
| Signal | `#00AEEF` | The current-position dot. Nowhere else. |
| Slate | `#55606F` (light bg) / `#9AA5B4` (dark bg) | Open ring, vector line, secondary text. |
| Paper | `#F4F6FA` | Light ground. |

## Minimum size

Never render the symbol below **16px**. Below that, use the wordmark alone.
Clear space on every side of the mark should equal the radius of the
current-position dot.
