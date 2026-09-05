import { EventBadge } from '@/components/EventBadge'
import { ObjectIdLink } from '@/components/ObjectIdLink'
import { Button } from '@/components/ui/button'
import { Clock, RotateCw } from 'lucide-react'
import type { TraceEvent } from '@/lib/api'
import { classifyEventSeverity } from '@/lib/eventSeverity'
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

/**
 * One incident/violation row: severity badge, target id/class, exact
 * timestamp, and a prominent Replay action that seeks the video straight to
 * this event -- the shared building block for every "incident stream" list
 * in the app (Live/Overview's Recent Events panel today; Investigation and
 * Alerts are natural future homes for the same component).
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
        'group flex items-center justify-between gap-2 px-3.5 py-2 transition-colors text-left cursor-pointer select-none',
        'hover:bg-surface-alt/50 focus-visible:outline-2 focus-visible:outline-accent focus-visible:-outline-offset-2',
        isSelected && 'bg-accent/10 border-l-2 border-l-accent',
        !isSelected && severity === 'danger' && 'bg-danger/5 border-l-2 border-l-danger',
        !isSelected && severity === 'warning' && 'border-l-2 border-l-warning',
        !isSelected && severity === 'info' && 'border-l-2 border-l-transparent',
        className,
      )}
    >
      <div className="flex items-start gap-2 min-w-0">
        <div className="flex flex-col gap-0.5 min-w-0">
          <div className="flex items-center gap-1.5">
            <EventBadge eventType={event.event_type} />
            <span className="text-xs font-mono font-medium text-ink">
              <ObjectIdLink objectId={event.object_id} onSelectObject={onSelectObject} /> {event.class_name}
            </span>
          </div>

          <div className="flex items-center gap-2 text-[11px] text-ink-subtle">
            <span className="flex items-center gap-0.5 font-mono tabular-nums">
              <Clock className="h-2.5 w-2.5 text-ink-subtle" />
              t={event.timestamp.toFixed(1)}s
            </span>
            {event.zone_id && (
              <span className="rounded bg-surface-alt px-1 py-0.2 text-[9px] font-mono text-ink-subtle">
                {event.zone_id}
              </span>
            )}
            {event.line_id && (
              <span className="rounded bg-surface-alt px-1 py-0.2 text-[9px] font-mono text-ink-subtle">
                {event.line_id}
              </span>
            )}
            {typeof event.metadata?.speed === 'number' && (
              <span className="font-mono text-danger font-semibold">
                {Math.round(event.metadata.speed as number)} km/h
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1.5 pl-2 shrink-0">
        <span className="text-[10px] font-mono text-ink-subtle tabular-nums">
          {Math.round(event.confidence * 100)}%
        </span>
        <Button
          type="button"
          variant="outline"
          size="xs"
          onClick={(e) => {
            e.stopPropagation()
            onSelect?.(event)
          }}
          aria-label={`Replay incident at ${event.timestamp.toFixed(1)} seconds`}
          className="h-6 gap-1 border-accent/40 text-accent hover:bg-accent/10 text-[10px] font-semibold px-1.5"
        >
          <RotateCw className="h-3 w-3" />
          <span className="hidden sm:inline">Replay</span>
        </Button>
      </div>
    </div>
  )
}
