import { describe, expect, it } from 'vitest'
import { ALL_EVENT_TYPES, classifyEventSeverity } from './eventSeverity'

describe('classifyEventSeverity', () => {
  it('classifies violations as danger', () => {
    expect(classifyEventSeverity('OVERSPEED')).toBe('danger')
    expect(classifyEventSeverity('ZONE_ENTERED')).toBe('danger')
    expect(classifyEventSeverity('SUDDEN_STOP')).toBe('danger')
  })

  it('classifies LINE_CROSSED as danger, consistent with the Live overlay and Analytics chart mappings', () => {
    expect(classifyEventSeverity('LINE_CROSSED')).toBe('danger')
  })

  it('classifies notable-but-lesser events as warning', () => {
    expect(classifyEventSeverity('STOPPED')).toBe('warning')
    expect(classifyEventSeverity('LOITERING')).toBe('warning')
  })

  it('classifies pure lifecycle events as info', () => {
    expect(classifyEventSeverity('OBJECT_APPEARED')).toBe('info')
    expect(classifyEventSeverity('OBJECT_DISAPPEARED')).toBe('info')
    expect(classifyEventSeverity('ZONE_EXITED')).toBe('info')
  })

  it('falls back to info for an unrecognized event type rather than throwing or rendering unstyled', () => {
    expect(classifyEventSeverity('SOME_FUTURE_EVENT_TYPE')).toBe('info')
  })

  it('covers every documented event type with a defined severity', () => {
    for (const type of ALL_EVENT_TYPES) {
      expect(['danger', 'warning', 'info']).toContain(classifyEventSeverity(type))
    }
  })
})
