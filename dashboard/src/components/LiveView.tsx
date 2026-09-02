import { useState } from 'react'
import { VideoPlayer, type SeekRequest } from '@/components/VideoPlayer'
import { RecentEventsFeed } from '@/components/RecentEventsFeed'
import { useCameraScene } from '@/hooks/useCameraScene'
import type { Camera, TraceEvent } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Sparkles, Layers, VideoOff, Video, Shapes, Minus } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface LiveViewProps {
  cameras: Camera[]
  selectedCameraId: string | null
  onSelectCamera: (cameraId: string | null) => void
  /** Phase 19: opens the Object Profile panel for a clicked #object_id. */
  onSelectObject?: (objectId: number) => void
  /** Phase 20: Demo scenarios and direct incident jump */
  externalSeekRequest?: SeekRequest | null
  onInvestigateEvent?: (eventId: number) => void
  activeScenarioTitle?: string | null
  onOpenDemoModal?: () => void
}

/**
 * The Live Monitoring workspace: the single highest-priority screen in
 * TRACE. Video is the dominant surface; the telemetry strip and the events
 * panel below it are real context for it, not filler -- `events` was
 * already being fetched here for the overlay's violation-state rendering
 * but was never actually shown anywhere on this page. Camera selection is
 * the single global one owned by App.tsx / the Header, not a page-local
 * duplicate.
 */
export function LiveView({
  cameras,
  selectedCameraId,
  onSelectCamera,
  onSelectObject,
  externalSeekRequest,
  onInvestigateEvent,
  activeScenarioTitle,
  onOpenDemoModal,
}: LiveViewProps) {
  const { video, trajectories, events, zones, lines, error } = useCameraScene(selectedCameraId)
  const selectedCamera = cameras.find((c) => c.camera_id === selectedCameraId)

  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)
  const [internalSeekRequest, setInternalSeekRequest] = useState<SeekRequest | null>(null)

  const effectiveSeekRequest = externalSeekRequest ?? internalSeekRequest

  function handleSelectEvent(event: TraceEvent) {
    setSelectedEventId(event.id)
    setInternalSeekRequest({ time: event.timestamp, nonce: Date.now() })
  }

  return (
    <div className="flex flex-col gap-4 max-w-[1600px] mx-auto w-full">
      {error && (
        <div role="alert" className="rounded-md border border-danger bg-danger/10 px-4 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      {cameras.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed border-border bg-surface-alt/30 py-10 text-center">
          <Video className="h-6 w-6 text-ink-disabled" />
          <p className="text-sm font-semibold text-ink">No cameras registered</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 items-start">
          {/* Camera switcher rail */}
          <div className="lg:col-span-2 flex flex-row gap-2 overflow-x-auto lg:flex-col lg:overflow-visible">
            {cameras.map((camera) => {
              const isActive = camera.camera_id === selectedCameraId
              return (
                <button
                  key={camera.camera_id}
                  type="button"
                  onClick={() => onSelectCamera(camera.camera_id)}
                  aria-current={isActive ? 'true' : undefined}
                  className={cn(
                    'flex shrink-0 items-center gap-2 rounded-lg border px-2.5 py-2 text-left transition-colors',
                    'focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-1',
                    isActive
                      ? 'border-accent bg-accent/10'
                      : 'border-border bg-surface hover:bg-surface-alt/50',
                  )}
                >
                  <div className="relative flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-surface-alt text-ink-subtle">
                    <Video className="h-3 w-3" />
                    {isActive && (
                      <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
                        <span className="motion-safe:absolute motion-safe:inline-flex h-full w-full motion-safe:animate-ping rounded-full bg-success opacity-75" />
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs font-semibold text-ink truncate">
                      {camera.name ?? camera.camera_id}
                    </span>
                    <span className="text-[10px] font-mono text-ink-subtle truncate">
                      {camera.camera_id}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>

          {/* Video workspace */}
          <div className="lg:col-span-7 flex flex-col gap-3">
            {/* Telemetry strip + Demo scenario action */}
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center divide-x divide-border rounded-md border border-border bg-surface shadow-2xs">
                <div className="flex items-center gap-1.5 px-3 py-1.5">
                  <Layers className="h-3 w-3 text-ink-subtle shrink-0" />
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-quiet">Tracks</span>
                  <span className="font-mono text-sm font-semibold tabular-nums text-ink">{trajectories.length}</span>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1.5">
                  <Shapes className="h-3 w-3 text-ink-subtle shrink-0" />
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-quiet">Zones</span>
                  <span className="font-mono text-sm font-semibold tabular-nums text-ink">{zones.length}</span>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1.5">
                  <Minus className="h-3 w-3 text-ink-subtle shrink-0" />
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-quiet">Lines</span>
                  <span className="font-mono text-sm font-semibold tabular-nums text-ink">{lines.length}</span>
                </div>
              </div>

              {onOpenDemoModal && (
                <Button
                  type="button"
                  variant="outline"
                  size="xs"
                  onClick={onOpenDemoModal}
                  className="gap-1.5 border-accent/40 bg-accent/5 text-ink hover:bg-accent/15 text-xs font-semibold shadow-2xs"
                >
                  <Sparkles className="h-3.5 w-3.5 text-secondary" />
                  <span>Demo Scenarios</span>
                </Button>
              )}
            </div>

            {video ? (
              <VideoPlayer
                video={video}
                trajectories={trajectories}
                events={events}
                zones={zones}
                lines={lines}
                seekRequest={effectiveSeekRequest}
                cameraName={selectedCamera?.name ?? selectedCameraId}
                onSelectObject={onSelectObject}
                onInvestigateEvent={onInvestigateEvent}
                activeScenarioTitle={activeScenarioTitle}
              />
            ) : (
              !error && (
                <div className="flex flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed border-border bg-surface-alt/30 py-10 text-center">
                  <VideoOff className="h-6 w-6 text-ink-disabled" />
                  <p className="text-sm font-semibold text-ink">No video registered for this camera yet</p>
                </div>
              )
            )}
          </div>

          {/* Events panel -- the camera's own event list was already being
              fetched for the overlay's violation-state coloring; it just
              had nowhere to actually be read on this page. */}
          <div className="lg:col-span-3 flex flex-col">
            <RecentEventsFeed
              events={events}
              selectedEventId={selectedEventId}
              onSelectEvent={handleSelectEvent}
              onSelectObject={onSelectObject}
            />
          </div>
        </div>
      )}
    </div>
  )
}
