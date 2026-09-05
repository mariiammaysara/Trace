import { describe, expect, it } from 'vitest'
import { extractEventRefs, formatToolCall, parseAnswerBlocks, parseInlineBold } from './agentInsights'

const realEvent = {
  id: 1,
  object_id: 134,
  camera_id: 'demo-trafficlight',
  event_type: 'LINE_CROSSED',
  class_name: 'car',
  timestamp: 9.5,
  confidence: 0.49,
  metadata: {},
  zone_id: null,
  line_id: 'crosswalk_tripwire',
}

describe('extractEventRefs', () => {
  it('extracts real events from a get_camera_events-shaped {events: [...]} result', () => {
    const result = { camera_id: 'demo-trafficlight', count: 1, events: [realEvent] }
    expect(extractEventRefs(result)).toEqual([realEvent])
  })

  it('extracts a single event from a get_event-shaped result (the event fields directly)', () => {
    expect(extractEventRefs(realEvent)).toEqual([realEvent])
  })

  it('filters out malformed entries in an events array rather than crashing', () => {
    const result = { events: [realEvent, { not: 'an event' }, null] }
    expect(extractEventRefs(result)).toEqual([realEvent])
  })

  it('returns no chips for tool results with no real event data (get_traffic_stats, errors)', () => {
    expect(extractEventRefs({ camera_id: 'demo', traffic_volume: 12 })).toEqual([])
    expect(extractEventRefs({ error: 'no camera with camera_id=\'nope\'' })).toEqual([])
  })
})

describe('formatToolCall', () => {
  it('formats real string and numeric arguments, quoting strings only', () => {
    expect(formatToolCall('get_camera_events', { camera_id: 'demo-trafficlight', event_type: 'LINE_CROSSED' })).toBe(
      'get_camera_events(camera_id="demo-trafficlight", event_type="LINE_CROSSED")',
    )
    expect(formatToolCall('get_object_stats', { object_id: 134 })).toBe('get_object_stats(object_id=134)')
  })

  it('omits null/undefined arguments and renders a bare call with none', () => {
    expect(formatToolCall('get_camera_events', { camera_id: 'demo', event_type: null })).toBe(
      'get_camera_events(camera_id="demo")',
    )
    expect(formatToolCall('get_traffic_stats', {})).toBe('get_traffic_stats()')
  })
})

describe('parseAnswerBlocks', () => {
  it('splits prose paragraphs from bullet groups', () => {
    const answer = 'Yes, a vehicle crossed the line.\n\n- Object ID: 134\n- Class: car\n- Timestamp: 9.5s'
    expect(parseAnswerBlocks(answer)).toEqual([
      { type: 'paragraph', text: 'Yes, a vehicle crossed the line.' },
      { type: 'bullets', items: ['Object ID: 134', 'Class: car', 'Timestamp: 9.5s'] },
    ])
  })

  it('joins wrapped paragraph lines with a space', () => {
    expect(parseAnswerBlocks('Line one\nline two continues.')).toEqual([
      { type: 'paragraph', text: 'Line one line two continues.' },
    ])
  })

  it('supports "*" bullets as well as "-"', () => {
    expect(parseAnswerBlocks('* first\n* second')).toEqual([{ type: 'bullets', items: ['first', 'second'] }])
  })
})

describe('parseInlineBold', () => {
  it('splits **bold** spans out of plain text', () => {
    expect(parseInlineBold('Estimated speed: **42 km/h**, above the limit')).toEqual([
      { text: 'Estimated speed: ', bold: false },
      { text: '42 km/h', bold: true },
      { text: ', above the limit', bold: false },
    ])
  })

  it('returns the whole string unbolded when there is no bold span', () => {
    expect(parseInlineBold('plain text')).toEqual([{ text: 'plain text', bold: false }])
  })
})
