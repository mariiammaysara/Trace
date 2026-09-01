/**
 * Event-type -> badge-severity mapping for the Event Investigation view
 * (Phase 10.3). A badge is one of tokens.css's explicitly-reserved semantic
 * surfaces ("event badges, alert toasts, status dots, violation chart
 * series"), so unlike src/lib/eventClassification.ts's chart-oriented
 * mapping (which uses brand `accent` as the default/non-violation bucket,
 * since a default chart series should be brand-colored), every event type
 * here resolves to one of TRACE's three semantic states -- never a brand
 * color. See dashboard/DESIGN_SYSTEM.md for the documented rationale per
 * type.
 */

export type EventSeverity = 'danger' | 'warning' | 'info'

export const ALL_EVENT_TYPES = [
  'LINE_CROSSED',
  'ZONE_ENTERED',
  'ZONE_EXITED',
  'OVERSPEED',
  'STOPPED',
  'SUDDEN_STOP',
  'LOITERING',
  'OBJECT_APPEARED',
  'OBJECT_DISAPPEARED',
] as const

/**
 * A restricted-zone entry, a speed violation, an anomalous sudden stop, or a
 * line crossing -- Section 11's "violation" framing. LINE_CROSSED is here
 * (not warning) specifically to stay consistent with the other two views
 * that already classify it as a danger-tier event: the Live overlay's flash
 * set (src/lib/overlay.ts's DANGER_EVENT_TYPES) and the Analytics chart's
 * violation set (src/lib/eventClassification.ts's VIOLATION_EVENT_TYPES).
 */
const DANGER_TYPES = new Set<string>(['OVERSPEED', 'ZONE_ENTERED', 'SUDDEN_STOP', 'LINE_CROSSED'])

/** Notable enough to want an investigator's attention, but not a hard violation on its own. */
const WARNING_TYPES = new Set<string>(['STOPPED', 'LOITERING'])

/** Pure lifecycle bookkeeping -- an object showed up, left, or exited a zone it was already flagged entering. */
const INFO_TYPES = new Set<string>(['OBJECT_APPEARED', 'OBJECT_DISAPPEARED', 'ZONE_EXITED'])

export function classifyEventSeverity(eventType: string): EventSeverity {
  if (DANGER_TYPES.has(eventType)) return 'danger'
  if (WARNING_TYPES.has(eventType)) return 'warning'
  if (INFO_TYPES.has(eventType)) return 'info'
  return 'info'
}
