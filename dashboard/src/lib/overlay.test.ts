import { describe, expect, it } from 'vitest'
import { findNearestPoint, getObjectViolationState } from './overlay'
import type { TraceEvent, TrackPoint } from './api'

function makeEvent(overrides: Partial<TraceEvent>): TraceEvent {
  return {
    id: 1,
    object_id: 1,
    event_type: 'OBJECT_APPEARED',
    class_name: 'person',
    timestamp: 0,
    confidence: 0.9,
    metadata: {},
    zone_id: null,
    line_id: null,
    ...overrides,
  }
}

function makePoint(overrides: Partial<TrackPoint>): TrackPoint {
  return { frame_id: 0, timestamp: 0, x: 0, y: 0, x_min: null, y_min: null, x_max: null, y_max: null, ...overrides }
}

describe('getObjectViolationState', () => {
  it('reads normal when there are no events for the object', () => {
    expect(getObjectViolationState(1, [], 5)).toBe('normal')
  })

  it('reads danger while inside a zone (between ZONE_ENTERED and ZONE_EXITED)', () => {
    const events = [
      makeEvent({ event_type: 'ZONE_ENTERED', timestamp: 1.0, zone_id: 'restricted' }),
      makeEvent({ event_type: 'ZONE_EXITED', timestamp: 4.0, zone_id: 'restricted' }),
    ]
    expect(getObjectViolationState(1, events, 0.5)).toBe('normal') // before entry
    expect(getObjectViolationState(1, events, 2.0)).toBe('danger') // inside
    expect(getObjectViolationState(1, events, 5.0)).toBe('normal') // after exit
  })

  it('reads danger during a brief flash window around a LINE_CROSSED event', () => {
    const events = [makeEvent({ event_type: 'LINE_CROSSED', timestamp: 10.0 })]
    expect(getObjectViolationState(1, events, 10.0)).toBe('danger')
    expect(getObjectViolationState(1, events, 10.3)).toBe('danger')
    expect(getObjectViolationState(1, events, 20.0)).toBe('normal')
  })

  it('reads warning (not danger) for a STOPPED event', () => {
    const events = [makeEvent({ event_type: 'STOPPED', timestamp: 5.0 })]
    expect(getObjectViolationState(1, events, 5.0)).toBe('warning')
  })

  it('ignores events belonging to a different object', () => {
    const events = [makeEvent({ object_id: 2, event_type: 'LINE_CROSSED', timestamp: 5.0 })]
    expect(getObjectViolationState(1, events, 5.0)).toBe('normal')
  })

  it('prioritizes danger over warning when both are active at once', () => {
    const events = [
      makeEvent({ event_type: 'STOPPED', timestamp: 5.0 }),
      makeEvent({ event_type: 'OVERSPEED', timestamp: 5.0 }),
    ]
    expect(getObjectViolationState(1, events, 5.0)).toBe('danger')
  })
})

describe('findNearestPoint', () => {
  it('returns the closest point within tolerance', () => {
    const points = [makePoint({ timestamp: 0 }), makePoint({ timestamp: 1 }), makePoint({ timestamp: 2 })]
    expect(findNearestPoint(points, 1.05)?.timestamp).toBe(1)
  })

  it('returns null when nothing is within tolerance', () => {
    const points = [makePoint({ timestamp: 0 }), makePoint({ timestamp: 10 })]
    expect(findNearestPoint(points, 5, 0.25)).toBeNull()
  })

  it('returns null for an empty points list', () => {
    expect(findNearestPoint([], 1)).toBeNull()
  })
})
