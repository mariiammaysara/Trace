import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { IncidentCard } from '@/components/IncidentCard'
import { queryAgent } from '@/lib/api'
import type { AgentAnswer, AgentToolCall } from '@/lib/api'
import {
  extractEventRefs,
  formatToolCall,
  parseAnswerBlocks,
  parseInlineBold,
  type AgentEventRef,
} from '@/lib/agentInsights'
import { Bot, Wrench, ChevronDown, CornerDownLeft, Loader2, Terminal } from 'lucide-react'
import { cn } from '@/lib/utils'

const EXAMPLE_QUERIES = [
  'Show events for camera demo.',
  'Did any object trigger an overspeed event?',
  "What's the traffic volume for camera demo?",
  'Tell me about tracked object 1.',
]

interface Turn {
  id: number
  question: string
  answer?: AgentAnswer
  error?: string
  pending?: boolean
}

let nextTurnId = 0

interface VisionAgentViewProps {
  /** Jumps to the Live page and seeks to this real event -- wired from
   * App.tsx (same demoSeekRequest mechanism the header's critical-breach
   * chip and demo scenarios already use). Omitted entirely when not
   * provided rather than rendering a dead button. */
  onReplayEvent?: (ref: AgentEventRef) => void
}

/** One real tool call the agent made this turn -- name and arguments are
 * exactly what was sent, expandable to the exact JSON the tool returned. */
function ToolCallPill({ call }: { call: AgentToolCall }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-fit items-center gap-1.5 rounded border border-border bg-surface-alt/60 px-2 py-1 font-mono text-[10px] text-ink-subtle hover:border-accent/40 hover:text-ink transition-colors"
      >
        <Wrench className="h-3 w-3 text-accent shrink-0" />
        <span>{formatToolCall(call.name, call.arguments)}</span>
        <ChevronDown className={cn('h-3 w-3 shrink-0 transition-transform', expanded && 'rotate-180')} />
      </button>
      {expanded && (
        <pre className="max-h-48 overflow-auto rounded border border-border bg-primary/60 p-2 font-mono text-[10px] text-ink-on-dark-quiet">
          {JSON.stringify(call.result, null, 2)}
        </pre>
      )}
    </div>
  )
}

/** The agent's free-text answer, lightly formatted (paragraphs, bullet
 * groups, **bold** spans) -- see lib/agentInsights.ts for exactly what this
 * does and doesn't parse. */
function AnswerText({ answer }: { answer: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      {parseAnswerBlocks(answer).map((block, i) =>
        block.type === 'paragraph' ? (
          <p key={i} className="text-sm text-ink leading-relaxed">
            {parseInlineBold(block.text).map((seg, j) =>
              seg.bold ? (
                <strong key={j} className="font-semibold text-ink">
                  {seg.text}
                </strong>
              ) : (
                <span key={j}>{seg.text}</span>
              ),
            )}
          </p>
        ) : (
          <ul key={i} className="flex flex-col gap-0.5 pl-4 text-sm text-ink list-disc marker:text-ink-subtle">
            {block.items.map((item, j) => (
              <li key={j} className="leading-relaxed">
                {parseInlineBold(item).map((seg, k) =>
                  seg.bold ? (
                    <strong key={k} className="font-semibold text-ink">
                      {seg.text}
                    </strong>
                  ) : (
                    <span key={k}>{seg.text}</span>
                  ),
                )}
              </li>
            ))}
          </ul>
        ),
      )}
    </div>
  )
}

/**
 * Ask TRACE: a real entry point to the Section 12 Vision Agent (POST
 * /agent/query), not a placeholder or a generic chat UI. Every answer is
 * grounded in real tool calls over the same data every other view reads
 * (src/agent/tools.py), shown alongside the answer for transparency --
 * expandable to the real JSON each tool returned, and (when a tool's result
 * carried real events) as clickable incident chips that jump straight to
 * that moment on the Live page. If no LLM API key is configured in this
 * environment, the backend returns a real 503 with a clear detail message
 * (src/api/deps.py); that is shown honestly, not hidden or faked.
 */
export function VisionAgentView({ onReplayEvent }: VisionAgentViewProps) {
  const [input, setInput] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // jsdom (this app's test environment) doesn't implement scrollTo --
    // same category of gap as HTMLMediaElement.play in LiveView.test.tsx.
    scrollRef.current?.scrollTo?.({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [turns])

  function ask(question: string) {
    const trimmed = question.trim()
    if (!trimmed) return
    setInput('')
    const id = nextTurnId++
    setTurns((prev) => [...prev, { id, question: trimmed, pending: true }])

    queryAgent(trimmed)
      .then((answer) => {
        setTurns((prev) => prev.map((t) => (t.id === id ? { id, question: trimmed, answer } : t)))
      })
      .catch((err: unknown) => {
        setTurns((prev) => prev.map((t) => (t.id === id ? { id, question: trimmed, error: String(err) } : t)))
      })
  }

  return (
    <div className="flex flex-col gap-3 max-w-4xl mx-auto w-full">
      <div className="flex items-center gap-2">
        <Terminal className="h-4 w-4 text-accent" />
        <span className="text-sm font-semibold text-ink">Vision Agent</span>
        <span className="rounded bg-accent/15 px-1.5 py-0.2 text-[9px] font-mono text-secondary">AI</span>
        <span className="text-[11px] text-ink-subtle">
          Grounded in real tool calls over TRACE's stored data -- never a guess
        </span>
      </div>

      <div className="flex flex-col overflow-hidden rounded-lg border border-border bg-surface shadow-2xs">
        <div ref={scrollRef} className="flex flex-col gap-4 overflow-y-auto p-4 min-h-[360px] max-h-[65vh]">
          {turns.length === 0 && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2 text-ink-subtle">
                <Bot className="h-8 w-8 text-ink-disabled shrink-0" />
                <p className="text-xs leading-relaxed">
                  Ask a question about tracked objects, events, zones, lines, or traffic --
                  every answer is backed by a real query against TRACE's own database, shown below it.
                </p>
              </div>
              <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle mt-1">
                Example queries
              </span>
              <div className="flex flex-col gap-1.5">
                {EXAMPLE_QUERIES.map((query) => (
                  <button
                    key={query}
                    type="button"
                    onClick={() => ask(query)}
                    className="flex w-fit items-center gap-1.5 rounded-md border border-border bg-surface-alt/40 px-3 py-1.5 text-left font-mono text-xs text-ink-quiet hover:border-accent hover:text-ink transition-colors"
                  >
                    <span className="text-accent">{'>'}</span>
                    {query}
                  </button>
                ))}
              </div>
            </div>
          )}

          {turns.map((turn) => {
            const eventRefs = turn.answer
              ? dedupeEventRefs(turn.answer.tool_calls.flatMap((call) => extractEventRefs(call.result)))
              : []

            return (
              <div key={turn.id} className="flex flex-col gap-2">
                <div className="flex items-start gap-1.5 font-mono text-xs text-ink-quiet">
                  <span className="text-accent shrink-0">{'>'}</span>
                  <span>{turn.question}</span>
                </div>

                {turn.pending && (
                  <div className="flex items-center gap-1.5 pl-4 text-xs text-ink-subtle">
                    <Loader2 className="h-3 w-3 animate-spin text-accent" />
                    <span>Reasoning over TRACE data…</span>
                  </div>
                )}

                {turn.error && (
                  <div role="alert" className="ml-4 rounded-md border border-danger bg-danger/10 px-3 py-2 text-xs text-danger">
                    {turn.error}
                  </div>
                )}

                {turn.answer && (
                  <div className="flex flex-col gap-2.5 pl-4 border-l-2 border-l-border">
                    {turn.answer.tool_calls.length > 0 && (
                      <div className="flex flex-col gap-1.5">
                        {turn.answer.tool_calls.map((call, i) => (
                          <ToolCallPill key={i} call={call} />
                        ))}
                      </div>
                    )}

                    <AnswerText answer={turn.answer.answer} />

                    {eventRefs.length > 0 && (
                      <div className="flex flex-col gap-1.5 rounded-md border border-border bg-surface-alt/30 overflow-hidden">
                        <span className="px-3 pt-2 text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">
                          Related incidents ({eventRefs.length})
                        </span>
                        <div className="divide-y divide-border/30">
                          {eventRefs.map((ref) => (
                            <IncidentCard key={ref.id} event={ref} onSelect={onReplayEvent ? () => onReplayEvent(ref) : undefined} />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault()
            ask(input)
          }}
          className="flex items-center gap-2 border-t border-border bg-surface-alt/20 px-3 py-2.5"
        >
          <span className="font-mono text-sm text-accent shrink-0">{'>'}</span>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about tracked objects, events, zones, or traffic…"
            className="flex-1 border-none bg-transparent font-mono text-sm shadow-none focus-visible:ring-0"
          />
          <Button type="submit" size="icon-sm" disabled={!input.trim()} aria-label="Ask">
            <CornerDownLeft className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}

function dedupeEventRefs(refs: AgentEventRef[]): AgentEventRef[] {
  const seen = new Set<number>()
  const result: AgentEventRef[] = []
  for (const ref of refs) {
    if (seen.has(ref.id)) continue
    seen.add(ref.id)
    result.push(ref)
  }
  return result
}
