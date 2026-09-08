import { useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { IncidentCard } from '@/components/IncidentCard'
import { Button } from '@/components/ui/button'
import {
  AlertTriangle,
  ChevronRight,
  Filter,
  Layers,
} from 'lucide-react'
import type { TraceEvent } from '@/lib/api'
import { classifyEventSeverity, type EventSeverity } from '@/lib/eventSeverity'
import { cn } from '@/lib/utils'

interface RecentEventsFeedProps {
  events: TraceEvent[]
  selectedEventId?: number | null
  onSelectEvent?: (event: TraceEvent) => void
  onViewAllEvents?: () => void
  /** Phase 19: opens the Object Profile panel for a clicked #object_id. */
  onSelectObject?: (objectId: number) => void
  className?: string
}

type FilterTier = 'all' | 'violations' | 'warnings'

/** Sort weight for the default "All" view -- danger and warning events
 * (real violations and notable-but-not-a-violation events) float above
 * info-tier lifecycle noise (OBJECT_APPEARED/DISAPPEARED, ZONE_EXITED). */
const SEVERITY_RANK: Record<EventSeverity, number> = { danger: 0, warning: 1, info: 2 }

export function RecentEventsFeed({
  events,
  selectedEventId,
  onSelectEvent,
  onViewAllEvents,
  onSelectObject,
  className,
}: RecentEventsFeedProps) {
  const [activeFilter, setActiveFilter] = useState<FilterTier>('all')

  const filteredEvents = events
    .filter((e) => {
      if (activeFilter === 'all') return true
      const severity = classifyEventSeverity(e.event_type)
      if (activeFilter === 'violations') return severity === 'danger'
      if (activeFilter === 'warnings') return severity === 'warning'
      return true
    })
    // Default grouping by severity (reusing eventSeverity.ts's own tiers, not
    // a new ranking): danger and warning events float above the lifecycle
    // noise (OBJECT_APPEARED/DISAPPEARED, ZONE_EXITED) that otherwise
    // dominates a long event list. A stable sort keeps each tier's original
    // (recency) order intact -- this only reorders across tiers.
    .sort((a, b) => SEVERITY_RANK[classifyEventSeverity(a.event_type)] - SEVERITY_RANK[classifyEventSeverity(b.event_type)])

  const violationCount = events.filter((e) => classifyEventSeverity(e.event_type) === 'danger').length
  const warningCount = events.filter((e) => classifyEventSeverity(e.event_type) === 'warning').length

  return (
    <Card className={cn('flex flex-col h-full overflow-hidden border-border bg-surface shadow-2xs', className)}>
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/50 px-4 py-2.5">
        <CardTitle className="text-sm font-semibold tracking-tight text-ink flex items-center gap-1.5">
          <AlertTriangle className="h-3.5 w-3.5 text-ink-subtle" />
          Recent Events
        </CardTitle>

        {onViewAllEvents && (
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={onViewAllEvents}
            className="text-xs text-ink-subtle hover:text-ink gap-0.5"
          >
            <span>Investigate</span>
            <ChevronRight className="h-3 w-3" />
          </Button>
        )}
      </CardHeader>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1 border-b border-border/40 bg-surface-alt/30 px-3 py-1.5 text-xs">
        <Filter className="h-3 w-3 text-ink-subtle mr-1 shrink-0" />
        <button
          type="button"
          onClick={() => setActiveFilter('all')}
          className={cn(
            'rounded px-2 py-0.5 text-[11px] font-medium transition-colors',
            activeFilter === 'all' ? 'bg-white/[0.06] text-ink font-semibold' : 'text-ink-subtle hover:text-ink',
          )}
        >
          All ({events.length})
        </button>

        <button
          type="button"
          onClick={() => setActiveFilter('violations')}
          className={cn(
            'rounded px-2 py-0.5 text-[11px] font-medium transition-colors flex items-center gap-1',
            activeFilter === 'violations' ? 'bg-white/[0.06] text-ink font-semibold' : 'text-ink-subtle hover:text-danger',
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
            activeFilter === 'warnings' ? 'bg-white/[0.06] text-ink font-semibold' : 'text-ink-subtle hover:text-warning',
          )}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-warning" />
          Warnings ({warningCount})
        </button>
      </div>

      <CardContent className="flex-1 overflow-y-auto p-0 min-h-[260px] max-h-[440px]">
        {filteredEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center h-full">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-alt text-ink-subtle mb-2">
              <Layers className="h-4 w-4" />
            </div>
            <p className="text-xs font-medium text-ink">No events detected</p>
            <p className="text-[11px] text-ink-subtle mt-0.5">
              {activeFilter === 'all'
                ? 'No events detected in the selected time range.'
                : 'No matching events for this severity filter.'}
            </p>
          </div>
        ) : (
          filteredEvents.map((event) => (
            <IncidentCard
              key={event.id}
              event={event}
              isSelected={selectedEventId === event.id}
              onSelect={onSelectEvent}
              onSelectObject={onSelectObject}
            />
          ))
        )}
      </CardContent>

      {/* Footer Info */}
      <div className="border-t border-border/40 bg-surface-alt/20 px-3 py-1.5 text-[10px] text-ink-subtle flex items-center justify-between">
        <span>Click a row to seek the video</span>
        <span className="font-mono tabular-nums">{filteredEvents.length} items</span>
      </div>
    </Card>
  )
}
