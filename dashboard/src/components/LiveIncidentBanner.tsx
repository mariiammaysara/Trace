import { useEffect, useState, useRef } from 'react'
import { EventBadge } from '@/components/EventBadge'
import { Button } from '@/components/ui/button'
import type { TraceEvent } from '@/lib/api'
import { ArrowRight, BellRing, X } from 'lucide-react'

interface LiveIncidentBannerProps {
  currentTime: number
  events: TraceEvent[]
  onInvestigateEvent: (eventId: number) => void
  activeScenarioTitle?: string | null
}

const EVENT_WINDOW_SECONDS = 0.5

export function LiveIncidentBanner({
  currentTime,
  events,
  onInvestigateEvent,
  activeScenarioTitle,
}: LiveIncidentBannerProps) {
  const [activeFiredEvent, setActiveFiredEvent] = useState<TraceEvent | null>(null)
  const [isDismissed, setIsDismissed] = useState(false)
  const lastFiredIdRef = useRef<number | null>(null)

  // Detect whenever currentTime crosses within ±0.5s of any real event in this video
  useEffect(() => {
    const matchingEvent = events.find(
      (e) => Math.abs(currentTime - e.timestamp) <= EVENT_WINDOW_SECONDS,
    )

    if (matchingEvent) {
      if (lastFiredIdRef.current !== matchingEvent.id) {
        lastFiredIdRef.current = matchingEvent.id
        setActiveFiredEvent(matchingEvent)
        setIsDismissed(false)
      }
    } else {
      // Clear after leaving the window if it wasn't recently fired
      if (activeFiredEvent && Math.abs(currentTime - activeFiredEvent.timestamp) > 2.0) {
        setActiveFiredEvent(null)
        lastFiredIdRef.current = null
      }
    }
  }, [currentTime, events, activeFiredEvent])

  if (!activeFiredEvent || isDismissed) {
    return null
  }

  return (
    <div
      role="region"
      aria-label="Real-time event notification"
      title={activeScenarioTitle ?? undefined}
      className="absolute bottom-3 left-3 z-30 flex max-w-[min(90%,20rem)] items-center gap-2 rounded-md border border-accent/60 bg-primary/95 px-2 py-1.5 shadow-xl backdrop-blur-md text-ink-on-dark animate-in fade-in-0 slide-in-from-bottom-2 duration-150"
    >
      <BellRing className="h-3.5 w-3.5 shrink-0 text-accent motion-safe:animate-bounce" />

      <div className="flex min-w-0 flex-col leading-tight">
        <div className="flex items-center gap-1 min-w-0">
          <EventBadge eventType={activeFiredEvent.event_type} />
          <span className="truncate font-mono text-[11px] text-ink-on-dark">
            #{activeFiredEvent.object_id} {activeFiredEvent.class_name}
          </span>
        </div>
        <span className="text-[9px] font-mono text-ink-on-dark-subtle">
          t={activeFiredEvent.timestamp.toFixed(2)}s
        </span>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        <Button
          type="button"
          size="icon-xs"
          onClick={() => onInvestigateEvent(activeFiredEvent.id)}
          aria-label="Investigate this event"
          title="Investigate"
          className="h-6 w-6 bg-accent hover:bg-accent/90 text-primary shadow-xs"
        >
          <ArrowRight className="h-3 w-3" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          onClick={() => setIsDismissed(true)}
          className="text-ink-on-dark-subtle hover:text-ink-on-dark h-6 w-6"
          aria-label="Dismiss event notification"
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
    </div>
  )
}
