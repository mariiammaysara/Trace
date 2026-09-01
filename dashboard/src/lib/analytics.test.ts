import { describe, expect, it } from 'vitest'
import { computeBusiestHours, formatHourLabel, formatSeconds } from './analytics'
import type { TraceEvent } from './api'

function makeEvent(overrides: Partial<TraceEvent>): TraceEvent {
  return {
    id: 1,
    object_id: 1,
    event_type: 'OBJECT_APPEARED',
    class_name: 'person',
    timestamp: 0,
    confidence: 1,
    metadata: {},
    zone_id: null,
    line_id: null,
    ...overrides,
  }
}

describe('computeBusiestHours', () => {
  it('returns 24 zero-filled hours for no events', () => {
    const result = computeBusiestHours([])
    expect(result).toHaveLength(24)
    expect(result.every((h) => h.count === 0)).toBe(true)
    expect(result[0]).toEqual({ hour: 0, count: 0 })
    expect(result[23]).toEqual({ hour: 23, count: 0 })
  })

  it('buckets events by their UTC hour of Unix-epoch timestamp', () => {
    // 2024-01-01T03:00:00Z and 2024-01-01T03:30:00Z both fall in hour 3;
    // 2024-01-01T14:00:00Z falls in hour 14.
    const events = [
      makeEvent({ timestamp: Date.UTC(2024, 0, 1, 3, 0, 0) / 1000 }),
      makeEvent({ timestamp: Date.UTC(2024, 0, 1, 3, 30, 0) / 1000 }),
      makeEvent({ timestamp: Date.UTC(2024, 0, 1, 14, 0, 0) / 1000 }),
    ]

    const result = computeBusiestHours(events)

    expect(result[3].count).toBe(2)
    expect(result[14].count).toBe(1)
    expect(result.reduce((sum, h) => sum + h.count, 0)).toBe(3)
  })

  it('buckets a near-zero video-relative timestamp into hour 0 (the documented file-source caveat)', () => {
    const result = computeBusiestHours([makeEvent({ timestamp: 12.5 })])
    expect(result[0].count).toBe(1)
  })
})

describe('formatSeconds', () => {
  it('formats to one decimal place with an "s" suffix', () => {
    expect(formatSeconds(3.14159)).toBe('3.1s')
    expect(formatSeconds(0)).toBe('0.0s')
  })
})

describe('formatHourLabel', () => {
  it('zero-pads single-digit hours', () => {
    expect(formatHourLabel(0)).toBe('00:00')
    expect(formatHourLabel(9)).toBe('09:00')
    expect(formatHourLabel(23)).toBe('23:00')
  })
})
