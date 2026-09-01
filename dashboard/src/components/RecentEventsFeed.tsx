import { useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { EventBadge } from '@/components/EventBadge'
import { Button } from '@/components/ui/button'
import {
  AlertTriangle,
  Clock,
  ChevronRight,
  Filter,
  Layers,
  Sparkles,
} from 'lucide-react'
import type { TraceEvent } from '@/lib/api'
import { classifyEventSeverity } from '@/lib/eventSeverity'
import { cn } from '@/lib/utils'

interface RecentEventsFeedProps {
  events: TraceEvent[]
  selectedEventId?: number | null
  onSelectEvent?: (event: TraceEvent) => void
  onViewAllEvents?: () => void
  className?: string
}

type FilterTier = 'all' | 'violations' | 'warnings'

export function RecentEventsFeed({
  events,
  selectedEventId,
  onSelectEvent,
  onViewAllEvents,
  className,
}: RecentEventsFeedProps) {
  const [activeFilter, setActiveFilter] = useState<FilterTier>('all')

  const filteredEvents = events.filter((e) => {
    if (activeFilter === 'all') return true
    const severity = classifyEventSeverity(e.event_type)
    if (activeFilter === 'violations') return severity === 'danger'
    if (activeFilter === 'warnings') return severity === 'warning'
    return true
  })

  const violationCount = events.filter((e) => classifyEventSeverity(e.event_type) === 'danger').length
  const warningCount = events.filter((e) => classifyEventSeverity(e.event_type) === 'warning').length

  return (
    <Card className={cn('flex flex-col h-full overflow-hidden border-border bg-surface shadow-2xs', className)}>
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/50 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <CardTitle className="text-sm font-semibold tracking-tight text-primary flex items-center gap-1.5">
            <AlertTriangle className="h-3.5 w-3.5 text-warning" />
            Recent Events
          </CardTitle>
          <span className="rounded-full bg-surface-alt px-1.5 py-0.2 text-[10px] font-mono font-medium text-secondary">
            {events.length}
          </span>
        </div>

        {onViewAllEvents && (
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={onViewAllEvents}
            className="text-xs text-secondary hover:text-primary gap-0.5"
          >
            <span>Investigate</span>
            <ChevronRight className="h-3 w-3" />
          </Button>
        )}
      </CardHeader>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1 border-b border-border/40 bg-surface-alt/30 px-3 py-1.5 text-xs">
        <Filter className="h-3 w-3 text-secondary/70 mr-1 shrink-0" />
        <button
          type="button"
          onClick={() => setActiveFilter('all')}
          className={cn(
            'rounded px-2 py-0.5 text-[11px] font-medium transition-colors',
            activeFilter === 'all'
              ? 'bg-surface text-primary shadow-2xs font-semibold'
              : 'text-secondary hover:text-primary',
          )}
        >
          All ({events.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveFilter('violations')}
          className={cn(
            'rounded px-2 py-0.5 text-[11px] font-medium transition-colors flex items-center gap-1',
            activeFilter === 'violations'
              ? 'bg-danger/10 text-danger font-semibold border border-danger/20'
              : 'text-secondary hover:text-danger',
          )}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-danger" />
          Violations ({violationCount})
        </button>

        <button
          type="button"
          onClick={() => setActiveFilter('warnings')}
          className={cn(
            'rounded px-2 py-0.5 text-[11px] font-medium transition-colors flex items-center gap-1',
            activeFilter === 'warnings'
              ? 'bg-warning/10 text-warning font-semibold border border-warning/20'
              : 'text-secondary hover:text-warning',
          )}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-warning" />
          Warnings ({warningCount})
        </button>
      </div>

      <CardContent className="flex-1 overflow-y-auto p-0 min-h-[260px] max-h-[440px] divide-y divide-border/30">
        {filteredEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center h-full">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-alt text-secondary mb-2">
              <Layers className="h-4 w-4" />
            </div>
            <p className="text-xs font-medium text-primary">No events detected</p>
            <p className="text-[11px] text-secondary mt-0.5">
              {activeFilter === 'all'
                ? 'No events detected in the selected time range.'
                : 'No matching events for this severity filter.'}
            </p>
          </div>
        ) : (
          filteredEvents.map((event) => {
            const severity = classifyEventSeverity(event.event_type)
            const isSelected = selectedEventId === event.id

            return (
              <div
                key={event.id}
                role="button"
                tabIndex={0}
                onClick={() => onSelectEvent?.(event)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onSelectEvent?.(event)
                  }
                }}
                className={cn(
                  'group flex items-center justify-between px-3.5 py-2 transition-colors text-left cursor-pointer select-none',
                  'hover:bg-surface-alt/50 focus-visible:outline-2 focus-visible:outline-accent focus-visible:-outline-offset-2',
                  isSelected && 'bg-accent/10 border-l-2 border-l-accent',
                  severity === 'danger' && 'border-l-2 border-l-danger',
                  severity === 'warning' && 'border-l-2 border-l-warning',
                  severity === 'info' && 'border-l-2 border-l-transparent',
                )}
              >
                <div className="flex items-start gap-2 min-w-0">
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <EventBadge eventType={event.event_type} />
                      <span className="text-xs font-mono font-medium text-primary">
                        #{event.object_id} {event.class_name}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[11px] text-secondary">
                      <span className="flex items-center gap-0.5 font-mono tabular-nums">
                        <Clock className="h-2.5 w-2.5 text-secondary/70" />
                        {event.timestamp.toFixed(1)}s
                      </span>
                      {event.zone_id && (
                        <span className="rounded bg-surface-alt px-1 py-0.2 text-[9px] font-mono text-secondary">
                          {event.zone_id}
                        </span>
                      )}
                      {event.line_id && (
                        <span className="rounded bg-surface-alt px-1 py-0.2 text-[9px] font-mono text-secondary">
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
                  <span className="text-[10px] font-mono text-secondary tabular-nums">
                    {Math.round(event.confidence * 100)}%
                  </span>
                  <div className="flex h-5 w-5 items-center justify-center rounded bg-surface-alt text-secondary opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight className="h-3 w-3" />
                  </div>
                </div>
              </div>
            )
          })
        )}
      </CardContent>

      {/* Footer Info */}
      <div className="border-t border-border/40 bg-surface-alt/20 px-3 py-1.5 text-[10px] text-secondary flex items-center justify-between">
        <span className="flex items-center gap-1">
          <Sparkles className="h-3 w-3 text-accent" />
          Click row to seek video
        </span>
        <span className="font-mono tabular-nums">{filteredEvents.length} items</span>
      </div>
    </Card>
  )
}
