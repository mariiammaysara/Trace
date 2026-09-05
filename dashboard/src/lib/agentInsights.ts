/**
 * Pure helpers for the Vision Agent view -- turning the two real things
 * POST /agent/query returns (a free-text `answer` and a `tool_calls` array
 * of {name, arguments, result}) into renderable pieces, without fabricating
 * anything the response didn't actually contain. No DOM/React here, kept
 * testable in isolation (same convention as lib/overlay.ts).
 */

/** Mirrors agent/tools.py's _event_to_dict() -- the one real event shape
 * every events-returning tool (get_camera_events, get_zone_events,
 * get_line_crossings, get_object_stats, get_event) actually returns. Unlike
 * the REST API's TraceEvent, this carries its own camera_id (the agent can
 * answer about any camera in one turn, not just the one currently selected
 * in the UI), which is exactly why a dedicated type is used here instead of
 * reusing api.ts's TraceEvent. */
export interface AgentEventRef {
  id: number
  object_id: number
  camera_id: string
  event_type: string
  class_name: string
  timestamp: number
  confidence: number
  metadata: Record<string, unknown>
  zone_id: string | null
  line_id: string | null
}

function isAgentEventRef(value: unknown): value is AgentEventRef {
  if (typeof value !== 'object' || value === null) return false
  const v = value as Record<string, unknown>
  return (
    typeof v.id === 'number' &&
    typeof v.object_id === 'number' &&
    typeof v.camera_id === 'string' &&
    typeof v.event_type === 'string' &&
    typeof v.class_name === 'string' &&
    typeof v.timestamp === 'number' &&
    typeof v.confidence === 'number'
  )
}

/**
 * Real events referenced by one tool call's result -- never a guess parsed
 * out of the LLM's free-text answer. Only recognizes the exact shapes
 * agent/tools.py actually returns: an {"events": [...]} wrapper
 * (get_camera_events/get_zone_events/get_line_crossings/get_object_stats),
 * or a single event returned directly (get_event). Anything else
 * (get_traffic_stats, get_video_segment, an {"error": ...} result) yields no
 * chips rather than a misleading guess.
 */
export function extractEventRefs(result: Record<string, unknown>): AgentEventRef[] {
  if (Array.isArray(result.events)) {
    return result.events.filter(isAgentEventRef)
  }
  if (isAgentEventRef(result)) {
    return [result]
  }
  return []
}

/** `get_camera_events(camera_id="demo-trafficlight", event_type="LINE_CROSSED")`
 * -- the real tool name and real arguments the agent actually called, not a
 * simulated/example call. */
export function formatToolCall(name: string, args: Record<string, unknown>): string {
  const parts = Object.entries(args)
    .filter(([, value]) => value !== undefined && value !== null)
    .map(([key, value]) => `${key}=${typeof value === 'string' ? `"${value}"` : String(value)}`)
  return `${name}(${parts.join(', ')})`
}

export type AnswerBlock = { type: 'paragraph'; text: string } | { type: 'bullets'; items: string[] }

/**
 * Splits the agent's free-text answer into paragraphs and "- "/"* " bullet
 * groups. Deliberately minimal (no tables, headings, code fences) -- the
 * agent's own system prompt (agent/prompts.py) asks for concise prose with
 * cited numbers, not a specific markdown dialect, so this covers what it
 * actually tends to produce rather than a full markdown spec nothing here
 * needs.
 */
export function parseAnswerBlocks(answer: string): AnswerBlock[] {
  const blocks: AnswerBlock[] = []
  let paragraphLines: string[] = []
  let bulletItems: string[] = []

  const flushParagraph = () => {
    if (paragraphLines.length > 0) {
      blocks.push({ type: 'paragraph', text: paragraphLines.join(' ').trim() })
      paragraphLines = []
    }
  }
  const flushBullets = () => {
    if (bulletItems.length > 0) {
      blocks.push({ type: 'bullets', items: bulletItems })
      bulletItems = []
    }
  }

  for (const rawLine of answer.split('\n')) {
    const line = rawLine.trim()
    if (line === '') {
      flushParagraph()
      flushBullets()
      continue
    }
    const bulletMatch = /^[-*]\s+(.*)$/.exec(line)
    if (bulletMatch) {
      flushParagraph()
      bulletItems.push(bulletMatch[1])
    } else {
      flushBullets()
      paragraphLines.push(line)
    }
  }
  flushParagraph()
  flushBullets()
  return blocks
}

export interface TextSegment {
  text: string
  bold: boolean
}

/** Splits inline `**bold**` spans out of one line/bullet's text. */
export function parseInlineBold(text: string): TextSegment[] {
  const segments: TextSegment[] = []
  const pattern = /\*\*(.+?)\*\*/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ text: text.slice(lastIndex, match.index), bold: false })
    }
    segments.push({ text: match[1], bold: true })
    lastIndex = pattern.lastIndex
  }
  if (lastIndex < text.length) {
    segments.push({ text: text.slice(lastIndex), bold: false })
  }
  return segments
}
