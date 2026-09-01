/**
 * Client-side computation of `busiest_hours` (Section 11), since GET
 * /analytics deliberately omits it from the bundle (see
 * src/lib/api.ts#getAnalytics) -- so the dashboard buckets the same raw
 * events GET /cameras/{id}/events already returns, using the exact same
 * "treat Event.timestamp as Unix epoch seconds" rule the backend's own
 * busiest_hours uses. That rule is only correct for live-camera sources;
 * for file-based sources (all of TRACE's current demo data) it buckets
 * everything into hour 0 UTC -- a real, documented limitation (see
 * TRACE_STUDY_GUIDE.md Section 11), not a bug in this bucketing.
 */

import type { TraceEvent } from './api'

export interface HourlyCount {
  hour: number
  count: number
}

/** All 24 hours, zero-filled, so a busiest-hours chart has a stable shape. */
export function computeBusiestHours(events: TraceEvent[]): HourlyCount[] {
  const counts = new Array<number>(24).fill(0)
  for (const event of events) {
    const hour = new Date(event.timestamp * 1000).getUTCHours()
    counts[hour] += 1
  }
  return counts.map((count, hour) => ({ hour, count }))
}

export function formatSeconds(value: number): string {
  return `${value.toFixed(1)}s`
}

export function formatHourLabel(hour: number): string {
  return `${hour.toString().padStart(2, '0')}:00`
}
