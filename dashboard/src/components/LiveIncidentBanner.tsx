import { useEffect, useState, useRef } from 'react'
import { EventBadge } from '@/components/EventBadge'
import { Button } from '@/components/ui/button'
import type { TraceEvent } from '@/lib/api'
import { ArrowRight, BellRing, Sparkles, X } from 'lucide-react'

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
      className="absolute bottom-16 left-1/2 -translate-x-1/2 z-30 flex items-center gap-3 rounded-lg border border-accent/60 bg-primary/95 px-4 py-2.5 shadow-2xl backdrop-blur-md text-ink-on-dark animate-in fade-in-0 slide-in-from-bottom-2 duration-150 max-w-lg w-[90%]"
    >
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent/20 text-accent">
        <BellRing className="h-4 w-4 motion-safe:animate-bounce" />
      </div>

      <div className="flex flex-col min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-accent">
            Live Event Fired
          </span>
          <span className="text-[10px] font-mono text-ink-on-dark-quiet">
            t={activeFiredEvent.timestamp.toFixed(2)}s
          </span>
          {activeScenarioTitle && (
            <span className="hidden sm:inline-flex items-center gap-1 rounded bg-white/10 px-1.5 py-0.2 text-[9px] font-medium text-ink-on-dark-subtle">
              <Sparkles className="h-2.5 w-2.5 text-accent" />
              {activeScenarioTitle}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 mt-0.5">
          <EventBadge eventType={activeFiredEvent.event_type} />
          <span className="text-xs text-ink-on-dark truncate">
            Target: <strong className="font-mono">#{activeFiredEvent.object_id} {activeFiredEvent.class_name}</strong>
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1.5 shrink-0">
        <Button
          type="button"
          size="xs"
          onClick={() => onInvestigateEvent(activeFiredEvent.id)}
          className="h-7 bg-accent hover:bg-accent/90 text-primary font-semibold text-[11px] gap-1 px-2.5 shadow-xs"
        >
          <span>Investigate</span>
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
