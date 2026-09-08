import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { EventBadge } from '@/components/EventBadge'
import { UploadVideoModal } from '@/components/UploadVideoModal'
import { RecentUploadsPanel, type UploadEntry } from '@/components/RecentUploadsPanel'
import { listCameraEvents, listCameraObjects, listVideos } from '@/lib/api'
import type { Camera, TraceEvent, Video as ApiVideo } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Video, MapPin, CheckCircle2, PlayCircle, UploadCloud } from 'lucide-react'

interface CamerasViewProps {
  cameras: Camera[]
  selectedCameraId: string | null
  onSelectCamera: (cameraId: string | null) => void
  onNavigateToLive?: () => void
  uploads?: UploadEntry[]
  onVideoUploaded?: (video: ApiVideo, cameraId: string, filename: string) => void
}

interface CameraStats {
  trackCount: number
  latestEvent: TraceEvent | null
  hasVideo: boolean
}

/**
 * The Camera Fleet page: one dense row per registered camera, not a card
 * grid -- a grid of a handful of cards next to a wall of empty space read
 * as unfinished regardless of styling; a row-based list stays intentional
 * whether there are 2 cameras or 50. Identity, active-track count, latest
 * event, and real stream availability (does this camera actually have a
 * registered video, i.e. would "View live" show anything) -- all built from
 * the real API (listCameraObjects/listCameraEvents/listVideos), same as
 * every other view. There is no per-camera health/FPS field in the backend
 * schema, so this deliberately does not show one rather than fabricate it.
 */
export function CamerasView({
  cameras,
  selectedCameraId,
  onSelectCamera,
  onNavigateToLive,
  uploads = [],
  onVideoUploaded,
}: CamerasViewProps) {
  const [stats, setStats] = useState<Record<string, CameraStats>>({})
  const [error, setError] = useState<string | null>(null)
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)

  function handleViewLive(cameraId: string) {
    onSelectCamera(cameraId)
    onNavigateToLive?.()
  }

  useEffect(() => {
    if (cameras.length === 0) return
    let cancelled = false

    Promise.all(
      cameras.map((camera) =>
        Promise.all([
          listCameraObjects(camera.camera_id),
          listCameraEvents(camera.camera_id),
          listVideos(camera.camera_id),
        ])
          .then(([objects, events, videos]): [string, CameraStats] => {
            const latestEvent = events.reduce<TraceEvent | null>(
              (latest, event) => (!latest || event.timestamp > latest.timestamp ? event : latest),
              null,
            )
            return [camera.camera_id, { trackCount: objects.length, latestEvent, hasVideo: videos.length > 0 }]
          })
          .catch((): [string, CameraStats] => [camera.camera_id, { trackCount: 0, latestEvent: null, hasVideo: false }]),
      ),
    )
      .then((entries) => {
        if (cancelled) return
        setStats(Object.fromEntries(entries))
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(String(err))
      })

    return () => {
      cancelled = true
    }
  }, [cameras])

  const uploadButton = (
    <Button type="button" size="sm" className="gap-1.5" onClick={() => setIsUploadModalOpen(true)}>
      <UploadCloud className="h-3.5 w-3.5" />
      Upload Video
    </Button>
  )

  const uploadModal = (
    <UploadVideoModal
      isOpen={isUploadModalOpen}
      onClose={() => setIsUploadModalOpen(false)}
      onUploaded={(video, cameraId, filename) => onVideoUploaded?.(video, cameraId, filename)}
    />
  )

  if (cameras.length === 0) {
    return (
      <div className="flex flex-col gap-4 max-w-4xl">
        <div className="flex justify-end">{uploadButton}</div>
        <RecentUploadsPanel uploads={uploads} onViewLive={handleViewLive} />
        <div className="flex flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed border-border bg-surface-alt/30 py-10 text-center">
          <Video className="h-6 w-6 text-ink-disabled" />
          <p className="text-sm font-semibold text-ink">No cameras registered</p>
          <p className="text-xs text-ink-subtle">Upload a video to register your first camera, or register one on the backend.</p>
        </div>
        {uploadModal}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 max-w-4xl">
      {error && (
        <div role="alert" className="rounded-md border border-danger bg-danger/10 px-4 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="flex justify-end">{uploadButton}</div>

      <RecentUploadsPanel uploads={uploads} onViewLive={handleViewLive} />

      <div className="flex items-center gap-4 px-3.5 text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">
        <span className="flex-1">Camera</span>
        <span className="w-20 text-right">Tracks</span>
        <span className="w-32 text-right">Latest event</span>
        <span className="w-28 text-right">Stream</span>
        <span className="w-24" />
      </div>

      <div className="rounded-lg border border-border bg-surface divide-y divide-border overflow-hidden">
        {cameras.map((camera) => {
          const isActive = camera.camera_id === selectedCameraId
          const cameraStats = stats[camera.camera_id]

          return (
            <div
              key={camera.camera_id}
              className={cn('flex items-center gap-4 px-3.5 py-2.5 transition-colors', isActive && 'bg-accent/5')}
            >
              <div className="flex flex-1 items-center gap-2.5 min-w-0">
                <div className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-surface-alt text-ink-subtle">
                  <Video className="h-3.5 w-3.5" />
                  <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
                    <span className="motion-safe:absolute motion-safe:inline-flex h-full w-full motion-safe:animate-ping rounded-full bg-success opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-success ring-2 ring-surface" />
                  </span>
                </div>
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-semibold text-ink truncate">
                      {camera.name ?? camera.camera_id}
                    </span>
                    {isActive && (
                      <span className="flex shrink-0 items-center gap-0.5 rounded-full border border-success/30 bg-success/10 px-1.5 py-0.2 text-[9px] font-medium text-success">
                        <CheckCircle2 className="h-2.5 w-2.5" />
                        Active
                      </span>
                    )}
                  </div>
                  <span className="flex items-center gap-1 text-[11px] font-mono text-ink-subtle truncate">
                    {camera.camera_id}
                    {camera.location && (
                      <span className="flex items-center gap-0.5 font-sans">
                        <MapPin className="h-2.5 w-2.5" />
                        {camera.location}
                      </span>
                    )}
                  </span>
                </div>
              </div>

              <span className="w-20 text-right font-mono text-sm font-semibold tabular-nums text-ink">
                {cameraStats ? cameraStats.trackCount : '—'}
              </span>

              <span className="w-32 flex justify-end">
                {cameraStats?.latestEvent ? (
                  <EventBadge eventType={cameraStats.latestEvent.event_type} />
                ) : (
                  <span className="text-xs text-ink-subtle">{cameraStats ? 'None yet' : '—'}</span>
                )}
              </span>

              <span className="w-28 text-right text-xs font-medium">
                {!cameraStats ? (
                  <span className="text-ink-subtle">—</span>
                ) : cameraStats.hasVideo ? (
                  <span className="text-success">Available</span>
                ) : (
                  <span className="text-ink-subtle">No video</span>
                )}
              </span>

              <span className="w-24 flex justify-end">
                <Button
                  type="button"
                  variant={isActive ? 'secondary' : 'outline'}
                  size="xs"
                  className="gap-1 text-[11px]"
                  onClick={() => {
                    onSelectCamera(camera.camera_id)
                    onNavigateToLive?.()
                  }}
                >
                  <PlayCircle className="h-3 w-3" />
                  View
                </Button>
              </span>
            </div>
          )
        })}
      </div>
      {uploadModal}
    </div>
  )
}
