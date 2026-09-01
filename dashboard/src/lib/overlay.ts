/**
 * Pure logic for syncing detection/tracking overlay state to video playback
 * time. No DOM/React here -- kept testable in isolation from rendering.
 */

import type { TraceEvent, TrackPoint } from './api'

export type ViolationState = 'danger' | 'warning' | 'normal'

/**
 * Event types that read as an active violation the moment they're
 * associated with an object -- Section 0/11's framing (a restricted-zone
 * entry, a speed/stop violation, a line crossing) is exactly what
 * --color-danger exists for, per the design system.
 */
const DANGER_EVENT_TYPES = new Set(['LINE_CROSSED', 'OVERSPEED', 'SUDDEN_STOP'])

/** Notable but less severe than a violation -- --color-warning. */
const WARNING_EVENT_TYPES = new Set(['STOPPED', 'LOITERING'])

/**
 * How long an instantaneous event (LINE_CROSSED, OVERSPEED, SUDDEN_STOP,
 * STOPPED, LOITERING -- none of which have a paired "end" event, unlike
 * ZONE_ENTERED/ZONE_EXITED) visually flashes on the overlay around its
 * timestamp. A deliberate, restrained choice, not a decorative one: without
 * some window a single-frame event would be visually imperceptible during
 * playback.
 */
const FLASH_WINDOW_SECONDS = 0.5

/**
 * The violation state one tracked object should render in at a given video
 * playback timestamp, derived from that object's real events -- never a
 * hardcoded/mock state.
 *
 * ZONE_ENTERED/ZONE_EXITED are treated as a real bracketed interval (the
 * object is "in danger" for as long as it's inside the zone, not just for a
 * flash) since both bracketing events exist in TRACE's schema. Every other
 * event type has no "end" event, so it gets the flash-window treatment
 * instead.
 */
export function getObjectViolationState(
  objectId: number,
  events: TraceEvent[],
  currentTime: number,
): ViolationState {
  const objectEvents = events.filter((event) => event.object_id === objectId)

  const zoneEvents = objectEvents
    .filter((event) => event.event_type === 'ZONE_ENTERED' || event.event_type === 'ZONE_EXITED')
    .sort((a, b) => a.timestamp - b.timestamp)

  let insideZone = false
  for (const event of zoneEvents) {
    if (event.timestamp > currentTime) break
    insideZone = event.event_type === 'ZONE_ENTERED'
  }
  if (insideZone) return 'danger'

  for (const event of objectEvents) {
    if (DANGER_EVENT_TYPES.has(event.event_type) && Math.abs(event.timestamp - currentTime) <= FLASH_WINDOW_SECONDS) {
      return 'danger'
    }
  }
  for (const event of objectEvents) {
    if (WARNING_EVENT_TYPES.has(event.event_type) && Math.abs(event.timestamp - currentTime) <= FLASH_WINDOW_SECONDS) {
      return 'warning'
    }
  }

  return 'normal'
}

/**
 * The trajectory point closest to the given video playback time, within
 * maxDelta seconds -- or null if nothing was sampled that close (the object
 * wasn't visible/tracked at that moment). Track points are sampled at the
 * pipeline's own frame rate, not continuous, so "nearest within tolerance"
 * is the correct match against a continuously-advancing video currentTime.
 */
export function findNearestPoint(
  points: TrackPoint[],
  currentTime: number,
  maxDelta = 0.25,
): TrackPoint | null {
  let nearest: TrackPoint | null = null
  let nearestDelta = Infinity

  for (const point of points) {
    const delta = Math.abs(point.timestamp - currentTime)
    if (delta < nearestDelta) {
      nearest = point
      nearestDelta = delta
    }
  }

  return nearest !== null && nearestDelta <= maxDelta ? nearest : null
}
