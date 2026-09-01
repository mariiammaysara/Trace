/**
 * Static per-event-type classification for analytics charts -- unlike
 * src/lib/overlay.ts's getObjectViolationState (which is time-windowed
 * against video playback), this just answers "does this event TYPE read as
 * a violation at all," for coloring a bar in an aggregate count chart.
 *
 * ZONE_ENTERED is included here (unlike overlay.ts's flash-based
 * DANGER_EVENT_TYPES, which brackets it separately) because
 * zone_violation_count -- a real Section 11 metric -- is literally
 * COUNT(ZONE_ENTERED); the two must agree on what counts as a violation.
 */

export type ChartVariant = 'danger' | 'warning' | 'accent'

const VIOLATION_EVENT_TYPES = new Set(['LINE_CROSSED', 'ZONE_ENTERED', 'OVERSPEED', 'SUDDEN_STOP'])
const WARNING_EVENT_TYPES = new Set(['STOPPED', 'LOITERING'])

export function classifyEventType(eventType: string): ChartVariant {
  if (VIOLATION_EVENT_TYPES.has(eventType)) return 'danger'
  if (WARNING_EVENT_TYPES.has(eventType)) return 'warning'
  return 'accent'
}
