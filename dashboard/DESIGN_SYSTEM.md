# TRACE Dashboard — Design System

> Colors are defined in [`theme/tokens.css`](./theme/tokens.css) and wired into
> Tailwind via `tailwind.config.js` / `src/index.css` — this file doesn't
> repeat that, it only adds what wasn't written down yet: type scale and the
> chart-color convention. See `tokens.css` for the full color rationale.

## Type scale

A small, fixed set of text styles. Every component picks from this list
rather than choosing font-size/weight ad hoc.

| Role | Classes | Used for |
|---|---|---|
| Page title | `text-2xl font-semibold text-primary` | View headings (e.g. "Analytics") |
| Card title | `text-base font-medium text-primary` | `CardTitle` content |
| Stat label | `text-xs font-medium uppercase tracking-wide text-secondary` | The small caption above a stat number (e.g. "OBJECT COUNT") |
| Stat value | `text-2xl font-semibold tabular-nums text-primary` (or `text-danger` for a violation stat) | The large number in a stat card |
| Body | `text-sm text-primary` | Default paragraph/UI text |
| Secondary / caption | `text-sm text-secondary` | De-emphasized text (timestamps, playback time, chart axis labels) |
| Fine print | `text-xs text-secondary` | Footnotes, caveats under a chart |

`tabular-nums` is required on any stat value or timer so digits don't shift
width as they change (already used by `LiveView`'s `currentTime`/`duration`
display — this table just names the convention).

## Chart color convention

- Default series (object counts, per-class breakdowns, hour-of-day volume):
  brand colors — `--color-accent` or `--color-secondary`. Never blue-as-decor;
  these *are* the brand blues, used because the data is normal activity, not
  because "charts are blue."
- A series or individual bar/point that specifically represents a violation
  or danger-class event (`LINE_CROSSED`, `ZONE_ENTERED`, `OVERSPEED`,
  `SUDDEN_STOP`) renders in `--color-danger`. A notable-but-lesser event
  (`STOPPED`, `LOITERING`) renders in `--color-warning`. This mirrors the
  classification already used for the Live View's detection overlay
  (`src/lib/overlay.ts`) — see `src/lib/eventClassification.ts` for the
  analytics-side (non-time-windowed) version of the same rule.
- Chart entrance: a bar animates from 0 to its real value once, on mount or
  when the underlying data changes (`transition-[width]`/`transition-[height]`,
  ~400–500ms ease-out, slight per-bar stagger). Never a looping or continuously
  re-triggering animation on data that hasn't changed.

## Cards

Stat summaries use shadcn's `Card`/`CardHeader`/`CardContent` (already themed
via `src/index.css`'s `--card`/`--card-foreground` mapping — see `StatCard`
in `src/components/StatCard.tsx`). A card representing a violation metric
(e.g. zone violations) additionally gets a subtle `ring-danger/40` and its
value in `text-danger`, so it's identifiable without reading the label.
