import { useState } from 'react'
import { VideoPlayer, type SeekRequest } from '@/components/VideoPlayer'
import { RecentEventsFeed } from '@/components/RecentEventsFeed'
import { useCameraScene } from '@/hooks/useCameraScene'
import type { Camera, TraceEvent } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Sparkles, Layers, VideoOff, Video, Shapes, Minus, AlertTriangle, Scan } from 'lucide-react'
import { Button } from '@/components/ui/button'

/** One cell of the telemetry strip above the video -- every value here is
 * real, already-fetched data (never estimated), see LiveView's own stats
 * for what backs each one. */
function TelemetryStat({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Layers
  label: string
  value: number
}) {
  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5">
      <Icon className="h-3 w-3 text-ink-subtle shrink-0" />
      <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-quiet">{label}</span>
      <span className="font-mono text-sm font-semibold tabular-nums text-ink">{value}</span>
    </div>
  )
}

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

  // Real per-frame detection count -- the sum of every tracked object's own
  // point history, i.e. how many actual bounding boxes the detector produced
  // for this camera, not an estimate. Processing FPS is deliberately not
  // shown here: the backend doesn't compute or expose a live per-camera FPS/
  // latency figure anywhere the frontend can read (see CamerasView.tsx's own
  // note on this), so surfacing one would mean fabricating it.
  const detectionCount = trajectories.reduce((sum, t) => sum + t.points.length, 0)

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
          {/* Video workspace -- the dominant column. The full-card camera
              rail that used to sit in its own 2-column strip is now a
              compact pill row above the telemetry strip: the same switching
              capability (name, live indicator, click-to-select), just not
              spending a whole always-visible column on it, so the video
              below gets that width back. */}
          <div className="lg:col-span-9 flex flex-col gap-3">
            <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5">
              {cameras.map((camera) => {
                const isActive = camera.camera_id === selectedCameraId
                return (
                  <button
                    key={camera.camera_id}
                    type="button"
                    onClick={() => onSelectCamera(camera.camera_id)}
                    aria-current={isActive ? 'true' : undefined}
                    title={camera.camera_id}
                    className={cn(
                      'flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors',
                      'focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-1',
                      isActive
                        ? 'border-accent bg-accent/10 text-ink'
                        : 'border-border bg-surface text-ink-subtle hover:bg-surface-alt/50 hover:text-ink',
                    )}
                  >
                    <span className="relative flex h-1.5 w-1.5 shrink-0">
                      {isActive && (
                        <span className="motion-safe:absolute motion-safe:inline-flex h-full w-full motion-safe:animate-ping rounded-full bg-success opacity-75" />
                      )}
                      <span className={cn('relative inline-flex h-1.5 w-1.5 rounded-full', isActive ? 'bg-success' : 'bg-ink-disabled')} />
                    </span>
                    <span className="max-w-[120px] truncate">{camera.name ?? camera.camera_id}</span>
                  </button>
                )
              })}
            </div>

            {/* Telemetry strip + Demo scenario action */}
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <div className="flex flex-wrap items-center divide-x divide-border rounded-md border border-border bg-surface shadow-2xs">
                <TelemetryStat icon={Layers} label="Tracks" value={trajectories.length} />
                <TelemetryStat icon={Shapes} label="Zones" value={zones.length} />
                <TelemetryStat icon={Minus} label="Lines" value={lines.length} />
                <TelemetryStat icon={AlertTriangle} label="Events" value={events.length} />
                <TelemetryStat icon={Scan} label="Detections" value={detectionCount} />
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
