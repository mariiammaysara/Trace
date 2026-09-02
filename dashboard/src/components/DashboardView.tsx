import { useEffect, useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { VideoPlayer, type SeekRequest } from '@/components/VideoPlayer'
import { RecentEventsFeed } from '@/components/RecentEventsFeed'
import { CameraFleetCard } from '@/components/CameraFleetCard'
import { BarChart, type BarChartDatum } from '@/components/charts/BarChart'
import { getAnalytics, listCameraObjects } from '@/lib/api'
import type { Camera, AnalyticsSummary, TraceEvent, TrackedObjectSummary } from '@/lib/api'
import { useCameraScene } from '@/hooks/useCameraScene'
import { classifyEventType } from '@/lib/eventClassification'
import { classifyEventSeverity } from '@/lib/eventSeverity'
import {
  Video,
  BarChart3,
  PieChart,
  AlertCircle,
  ChevronRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface DashboardViewProps {
  cameras: Camera[]
  selectedCameraId: string | null
  onSelectCamera: (cameraId: string | null) => void
  isApiConnected?: boolean
  onNavigateToEvents?: () => void
  onNavigateToAnalytics?: () => void
}

export function DashboardView({
  cameras,
  selectedCameraId,
  onSelectCamera,
  isApiConnected = true,
  onNavigateToEvents,
  onNavigateToAnalytics,
}: DashboardViewProps) {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null)
  const [cameraObjects, setCameraObjects] = useState<TrackedObjectSummary[]>([])
  const [analyticsError, setAnalyticsError] = useState<string | null>(null)

  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)
  const [seekRequest, setSeekRequest] = useState<SeekRequest | null>(null)

  // Active camera scene (video, trajectories, events, zones, lines)
  const { video, trajectories, events, zones, lines, error: sceneError } = useCameraScene(selectedCameraId)

  // 3. Fetch analytics & object counts for active camera
  useEffect(() => {
    if (!selectedCameraId) return
    let cancelled = false
    setAnalyticsError(null)

    Promise.all([
      getAnalytics(selectedCameraId).catch(() => null),
      listCameraObjects(selectedCameraId).catch(() => []),
    ])
      .then(([summary, objects]) => {
        if (cancelled) return
        if (summary) setAnalytics(summary)
        setCameraObjects(objects)
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

  // Derived real metrics
  const trackedCount = analytics?.object_count ?? cameraObjects.length ?? trajectories.length
  const totalEventsCount = events.length
  const violationCount = events.filter((e) => classifyEventSeverity(e.event_type) === 'danger').length

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

  return (
    <div className="flex flex-col gap-4 max-w-[1600px] mx-auto w-full">
      {/* Global Error Banner if API Fails */}
      {error && (
        <div role="alert" className="flex items-center gap-2 rounded-lg border border-danger/40 bg-danger/10 px-4 py-2.5 text-xs text-danger font-medium">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* System status -- tier 1 of Overview's hierarchy. One slim strip,
          not a row of cards: this is context for what follows, not the
          page's subject. Real state only (isApiConnected mirrors whether
          the last listCameras() call actually succeeded). */}
      <div className="flex flex-wrap items-center divide-x divide-border rounded-md border border-border bg-surface">
        <div className="flex items-center gap-1.5 px-3.5 py-2">
          <span className={cn('h-1.5 w-1.5 rounded-full', isApiConnected ? 'bg-success' : 'bg-danger')} />
          <span className="text-xs font-medium text-ink">{isApiConnected ? 'System operational' : 'System offline'}</span>
        </div>
        <div className="flex items-center gap-1.5 px-3.5 py-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Cameras</span>
          <span className="font-mono text-sm font-semibold text-ink">{cameras.length}</span>
        </div>
        <div className="flex items-center gap-1.5 px-3.5 py-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Tracked</span>
          <span className="font-mono text-sm font-semibold text-ink">{trackedCount}</span>
        </div>
        <div className="flex items-center gap-1.5 px-3.5 py-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Events</span>
          <span className="font-mono text-sm font-semibold text-ink">{totalEventsCount}</span>
          {violationCount > 0 && (
            <span className="font-mono text-xs font-semibold text-danger">· {violationCount} violation{violationCount === 1 ? '' : 's'}</span>
          )}
        </div>
      </div>

      {/* Primary Operations Section: Live Feed (68%) + Recent Events (32%) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 items-start">
        {/* Left Column: Live Video Feed Card */}
        <div className="lg:col-span-8 flex flex-col gap-2">
          <Card size="sm" className="border-border bg-surface shadow-2xs overflow-hidden">
            <CardHeader className="flex flex-row items-center border-b border-border/50">
              <CardTitle className="text-sm font-semibold tracking-tight text-ink flex items-center gap-1.5">
                <Video className="h-3.5 w-3.5 text-ink-subtle" />
                Live Monitoring
              </CardTitle>
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
