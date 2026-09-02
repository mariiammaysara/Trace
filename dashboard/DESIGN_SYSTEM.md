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
| Stat label | `text-xs font-semibold uppercase tracking-wide text-primary/80` | The small caption above a stat number (e.g. "OBJECT COUNT") — `font-semibold` + `text-primary/80` rather than `text-secondary`, since a small tracked-out uppercase caption needs more weight than `text-secondary`'s ~4.5:1 ratio gives it to stay legible at that size |
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

## Event badges (Event Investigation, Phase 10.3)

A badge is one of `tokens.css`'s explicitly-reserved semantic-color
surfaces ("event badges, alert toasts, status dots, violation chart
series"), so unlike the chart convention above — where only violation-class
data gets a semantic color and everything else stays brand — **every**
event-type badge resolves to one of TRACE's three semantic states, never a
brand color. Implemented in `src/lib/eventSeverity.ts`
(`classifyEventSeverity`) and rendered by `src/components/EventBadge.tsx`.

| Event type | Severity | Why |
|---|---|---|
| `OVERSPEED` | `danger` | A speed violation — Section 11's own "violation" framing. |
| `ZONE_ENTERED` | `danger` | Entering a configured zone reads as a violation when that zone is restricted — `zone_violation_count` (Section 11) is literally `COUNT(ZONE_ENTERED)`. |
| `SUDDEN_STOP` | `danger` | An anomalous, potentially hazardous motion event (Section 4/7). |
| `LINE_CROSSED` | `danger` | Kept in the danger tier here to stay **consistent with the other two views**, not because badges alone demand it: the Live overlay's flash set (`overlay.ts`'s `DANGER_EVENT_TYPES`) and the Analytics chart's violation set (`eventClassification.ts`'s `VIOLATION_EVENT_TYPES`) both already treat `LINE_CROSSED` as danger-tier. An earlier draft of this table put it at `warning` — a real cross-view inconsistency, caught and fixed; see `src/lib/eventColorConsistency.test.ts`, which now asserts all three mappings agree. |
| `STOPPED` | `warning` | Notable but not urgent on its own. |
| `LOITERING` | `warning` | Section 0's own "suspicious behavior" framing — notable, not an automatic violation. |
| `OBJECT_APPEARED` | `info` | Pure lifecycle bookkeeping. |
| `OBJECT_DISAPPEARED` | `info` | Pure lifecycle bookkeeping. |
| `ZONE_EXITED` | `info` | The closing half of a zone visit already flagged on entry — not itself a new violation. |

Any event type outside this fixed list (there shouldn't be one — Section 7
defines exactly these nine) falls back to `info` rather than silently
rendering unstyled.

Badge classes: `border-{severity}/30 bg-{severity}/10 text-{severity}` on
top of shadcn's `Badge` `variant="outline"`.

**Cross-view consistency**: the badge severity tier (danger/warning/"non-severe")
for every event type must match the Live overlay (`overlay.ts`) and the
Analytics chart (`eventClassification.ts`). The one place the *literal color*
is allowed to differ is the non-severe bucket — badges render it as
`--color-info` (a badge is a reserved semantic surface), while the overlay
and chart render it as brand `accent` (their default/non-violation series
color) — but the tier itself (not danger, not warning) must still agree.
`src/lib/eventColorConsistency.test.ts` checks this directly across all
three modules so a future change to one can't silently drift from the
others.
