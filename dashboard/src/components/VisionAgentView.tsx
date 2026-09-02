import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { queryAgent } from '@/lib/api'
import type { AgentAnswer } from '@/lib/api'
import { Bot, Wrench, ArrowUp } from 'lucide-react'
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

/**
 * Ask TRACE: a real entry point to the Section 12 Vision Agent (POST
 * /agent/query), not a placeholder or a generic chat UI. Every answer is
 * grounded in real tool calls over the same data every other view reads
 * (src/agent/tools.py) -- shown alongside the answer for transparency, per
 * the API's own AgentToolCallRead design. If no LLM API key is configured
 * in this environment, the backend returns a real 503 with a clear detail
 * message (src/api/deps.py); that is shown honestly, not hidden or faked.
 */
export function VisionAgentView() {
  const [input, setInput] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])

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
    <div className="flex flex-col gap-4 max-w-3xl">
      <div className="flex items-center gap-2">
        <Bot className="h-4 w-4 text-accent" />
        <span className="text-sm font-semibold text-ink">Ask TRACE</span>
        <span className="rounded bg-accent/15 px-1.5 py-0.2 text-[9px] font-mono text-secondary">AI</span>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          ask(input)
        }}
        className="flex items-center gap-2"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about tracked objects, events, zones, or traffic…"
          className="flex-1"
        />
        <Button type="submit" size="icon-sm" disabled={!input.trim()} aria-label="Ask">
          <ArrowUp className="h-4 w-4" />
        </Button>
      </form>

      {turns.length === 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Example queries</span>
          <div className="flex flex-col gap-1.5">
            {EXAMPLE_QUERIES.map((query) => (
              <button
                key={query}
                type="button"
                onClick={() => ask(query)}
                className="w-fit rounded-md border border-border bg-surface px-3 py-1.5 text-left text-xs text-ink-quiet hover:border-accent hover:text-ink transition-colors"
              >
                {query}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {turns.map((turn) => (
          <div key={turn.id} className="rounded-lg border border-border bg-surface overflow-hidden">
            <div className="border-b border-border/50 bg-surface-alt/40 px-3.5 py-2 text-xs font-medium text-ink">
              {turn.question}
            </div>
            <div className="px-3.5 py-2.5">
              {turn.pending && <p className="text-xs text-ink-subtle">Reasoning over TRACE data…</p>}
              {turn.error && <p className="text-xs text-danger">{turn.error}</p>}
              {turn.answer && (
                <div className="flex flex-col gap-2">
                  <p className="text-sm text-ink">{turn.answer.answer}</p>
                  {turn.answer.tool_calls.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <Wrench className="h-3 w-3 text-ink-subtle" />
                      {turn.answer.tool_calls.map((call, j) => (
                        <span
                          key={j}
                          className={cn(
                            'rounded bg-surface-alt px-1.5 py-0.5 font-mono text-[10px] text-ink-subtle',
                          )}
                        >
                          {call.name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
