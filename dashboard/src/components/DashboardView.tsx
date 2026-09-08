import { useEffect, useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { VideoPlayer, type SeekRequest } from '@/components/VideoPlayer'
import { RecentEventsFeed } from '@/components/RecentEventsFeed'
import { CameraFleetCard } from '@/components/CameraFleetCard'
import { BarChart, type BarChartDatum } from '@/components/charts/BarChart'
import { getAnalytics } from '@/lib/api'
import type { Camera, AnalyticsSummary, TraceEvent } from '@/lib/api'
import { useCameraScene } from '@/hooks/useCameraScene'
import { classifyEventType } from '@/lib/eventClassification'
import {
  Video,
  BarChart3,
  PieChart,
  AlertCircle,
  ChevronRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'

interface DashboardViewProps {
  cameras: Camera[]
  selectedCameraId: string | null
  onSelectCamera: (cameraId: string | null) => void
  onNavigateToEvents?: () => void
  onNavigateToAnalytics?: () => void
}

export function DashboardView({
  cameras,
  selectedCameraId,
  onSelectCamera,
  onNavigateToEvents,
  onNavigateToAnalytics,
}: DashboardViewProps) {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null)
  const [analyticsError, setAnalyticsError] = useState<string | null>(null)

  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)
  const [seekRequest, setSeekRequest] = useState<SeekRequest | null>(null)
  // Real resolution once the browser actually loads the stream -- there is
  // no resolution/fps field on the Video record itself (src/lib/api.ts), so
  // this is the only honest source for it, and it's null (shown as nothing,
  // not a guess) until onLoadedMetadata actually fires.
  const [videoResolution, setVideoResolution] = useState<{ width: number; height: number } | null>(null)

  // Active camera scene (video, trajectories, events, zones, lines)
  const { video, trajectories, events, zones, lines, error: sceneError } = useCameraScene(selectedCameraId)

  // Fetch analytics (per-class/event-frequency charts) for the active camera
  useEffect(() => {
    setVideoResolution(null)
    if (!selectedCameraId) return
    let cancelled = false
    setAnalyticsError(null)

    getAnalytics(selectedCameraId)
      .then((summary) => {
        if (!cancelled) setAnalytics(summary)
      })
      .catch((err: unknown) => {
        if (!cancelled) setAnalyticsError(String(err))
      })

    return () => {
      cancelled = true
    }
  }, [selectedCameraId])

  function handleSelectEvent(event: TraceEvent) {
    setSelectedEventId(event.id)
    setSeekRequest({ time: event.timestamp, nonce: Date.now() })
  }

  const selectedCamera = cameras.find((c) => c.camera_id === selectedCameraId)
  const error = sceneError ?? analyticsError

  // Chart data: Object distribution from real per_class_stats
  const perClassObjectData: BarChartDatum[] = analytics?.per_class_stats
    ? Object.entries(analytics.per_class_stats)
        .sort((a, b) => b[1].object_count - a[1].object_count)
        .map(([className, stats]) => ({
          key: className,
          label: className,
          value: stats.object_count,
          variant: 'secondary',
        }))
    : []

  // Chart data: Event frequency with semantic colors
  const eventFrequencyData: BarChartDatum[] = analytics?.event_frequency
    ? Object.entries(analytics.event_frequency)
        .sort((a, b) => b[1] - a[1])
        .map(([eventType, count]) => ({
          key: eventType,
          label: eventType,
          value: count,
          variant: classifyEventType(eventType),
        }))
    : []

  // The video card's context line -- real camera id, real resolution (once
  // known), and the pipeline's real, actually-deployed architecture. No FPS
  // reading (not exposed anywhere) and no "calibrated" claim: every
  // configured camera's homography is illustrative/placeholder only (see
  // configs/cameras/*.json's own comments), so "geometry," not "calibrated."
  const contextLine = [
    selectedCameraId ? selectedCameraId.toUpperCase() : null,
    videoResolution ? `${videoResolution.height}p` : null,
  ]
    .filter(Boolean)
    .join(' // ')

  return (
    <div className="flex flex-col gap-4 max-w-[1600px] mx-auto w-full">
      {/* Global Error Banner if API Fails */}
      {error && (
        <div role="alert" className="flex items-center gap-2 rounded-lg border border-danger/40 bg-danger/10 px-4 py-2.5 text-xs text-danger font-medium">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Primary Operations Section: Live Feed (68%) + Recent Events (32%) --
          the actual operational content, first thing on the page. */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 items-start">
        {/* Left Column: Live Video Feed Card */}
        <div className="lg:col-span-8 flex flex-col gap-2">
          <Card size="sm" className="border-border bg-surface shadow-2xs overflow-hidden">
            <CardHeader className="flex flex-row items-center border-b border-border/50 py-2">
              <div className="flex items-center gap-1.5 min-w-0 overflow-hidden whitespace-nowrap font-mono text-[11px] text-ink-subtle">
                {contextLine && <span className="text-ink font-semibold">{contextLine}</span>}
                {contextLine && <span className="text-border">•</span>}
                <span>YOLOv8n + ByteTrack</span>
                <span className="text-border">•</span>
                <span>Planar homography geometry</span>
              </div>
            </CardHeader>

            <CardContent>
              {video ? (
                <VideoPlayer
                  video={video}
                  trajectories={trajectories}
                  events={events}
                  zones={zones}
                  lines={lines}
                  seekRequest={seekRequest}
                  cameraName={selectedCamera?.name ?? selectedCameraId}
                  onVideoMetadata={setVideoResolution}
                />
              ) : (
                <div className="flex flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-border bg-surface-alt/30 py-10 text-center">
                  <Video className="h-5 w-5 text-ink-disabled mb-1" />
                  <p className="text-sm font-medium text-ink">No video for this camera</p>
                  <p className="text-xs text-ink-subtle">
                    Select an active camera or register a video stream.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Recent Events Feed */}
        <div className="lg:col-span-4 flex flex-col">
          <RecentEventsFeed
            events={events}
            selectedEventId={selectedEventId}
            onSelectEvent={handleSelectEvent}
            onViewAllEvents={onNavigateToEvents}
          />
        </div>
      </div>

      {/* Analytics Overview Section: 3 Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Card A: Object Distribution */}
        <Card size="sm" className="border-border bg-surface shadow-2xs">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border/50">
            <CardTitle className="text-xs font-semibold tracking-tight text-ink flex items-center gap-1.5">
              <PieChart className="h-3.5 w-3.5 text-ink-subtle" />
              Object Distribution
            </CardTitle>
            <span className="font-mono text-[10px] text-ink-subtle">
              {perClassObjectData.length} classes
            </span>
          </CardHeader>
          <CardContent>
            <BarChart
              data={perClassObjectData}
              emptyMessage="No object classifications available yet."
            />
          </CardContent>
        </Card>

        {/* Card B: Event Frequency */}
        <Card size="sm" className="border-border bg-surface shadow-2xs">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border/50">
            <CardTitle className="text-xs font-semibold tracking-tight text-ink flex items-center gap-1.5">
              <BarChart3 className="h-3.5 w-3.5 text-ink-subtle" />
              Event Breakdown
            </CardTitle>
            {onNavigateToAnalytics ? (
              <Button
                type="button"
                variant="ghost"
                size="xs"
                onClick={onNavigateToAnalytics}
                className="text-[10px] text-ink-subtle hover:text-ink gap-0.5 h-5 px-1.5"
              >
                <span>Details</span>
                <ChevronRight className="h-3 w-3" />
              </Button>
            ) : (
              <span className="font-mono text-[10px] text-ink-subtle">
                {eventFrequencyData.length} types
              </span>
            )}
          </CardHeader>
          <CardContent>
            <BarChart
              data={eventFrequencyData}
              emptyMessage="No events recorded for this camera."
            />
          </CardContent>
        </Card>

        {/* Card C: Camera Fleet */}
        <CameraFleetCard
          cameras={cameras}
          activeCameraId={selectedCameraId}
          onSelectCamera={onSelectCamera}
        />
      </div>
    </div>
  )
}
