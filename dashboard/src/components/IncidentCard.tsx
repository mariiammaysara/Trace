import { ObjectIdLink } from '@/components/ObjectIdLink'
import { Button } from '@/components/ui/button'
import { RotateCw } from 'lucide-react'
import type { TraceEvent } from '@/lib/api'
import { classifyEventSeverity, type EventSeverity } from '@/lib/eventSeverity'
import { cn } from '@/lib/utils'

interface IncidentCardProps {
  event: TraceEvent
  isSelected?: boolean
  /** Selecting the incident (row click or the Replay button) -- the caller
   * is what actually seeks the video; this component only reports intent. */
  onSelect?: (event: TraceEvent) => void
  /** Phase 19: opens the Object Profile panel for the target's #object_id. */
  onSelectObject?: (objectId: number) => void
  className?: string
}

/** Plain colored text per severity -- no pill/border chrome here. Reserves
 * color for what it actually means (a confirmed violation reads in
 * --color-danger); a badge shape would just be decoration on top of that. */
const SEVERITY_TEXT: Record<EventSeverity, string> = {
  danger: 'text-danger',
  warning: 'text-warning',
  info: 'text-ink-subtle',
}

/**
 * One incident row: timestamp, event type, target -- a single dense line,
 * not a two-line card. The shared building block for every "incident
 * stream" list in the app (Live/Overview's Recent Events panel today; the
 * Vision Agent's "related incidents" chips reuse it too).
 */
export function IncidentCard({ event, isSelected, onSelect, onSelectObject, className }: IncidentCardProps) {
  const severity = classifyEventSeverity(event.event_type)

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(event)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect?.(event)
        }
      }}
      className={cn(
        'group flex h-10 items-center justify-between gap-2 border-b border-border/40 px-3 text-left cursor-pointer select-none transition-colors',
        'hover:bg-white/[0.02] focus-visible:outline-2 focus-visible:outline-accent focus-visible:-outline-offset-2',
        isSelected && 'bg-white/[0.04]',
        className,
      )}
    >
      <div className="flex items-center gap-2.5 min-w-0 font-mono text-xs">
        <span className="text-ink-subtle tabular-nums shrink-0">{event.timestamp.toFixed(1)}s</span>
        <span className={cn('font-semibold shrink-0', SEVERITY_TEXT[severity])}>{event.event_type}</span>
        <span className="text-ink truncate">
          <ObjectIdLink objectId={event.object_id} onSelectObject={onSelectObject} /> {event.class_name}
        </span>
      </div>

      <div className="flex items-center gap-2 pl-2 shrink-0">
        <span className="text-[10px] font-mono text-ink-subtle tabular-nums">
          {Math.round(event.confidence * 100)}%
        </span>
        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          onClick={(e) => {
            e.stopPropagation()
            onSelect?.(event)
          }}
          aria-label={`Replay incident at ${event.timestamp.toFixed(1)} seconds`}
          className="text-ink-subtle opacity-0 transition-opacity group-hover:opacity-100 hover:text-ink hover:bg-white/[0.06]"
        >
          <RotateCw className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}
