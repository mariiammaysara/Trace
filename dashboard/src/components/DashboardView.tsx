import { useEffect, useState } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { StatCard } from '@/components/StatCard'
import { VideoPlayer, type SeekRequest } from '@/components/VideoPlayer'
import { RecentEventsFeed } from '@/components/RecentEventsFeed'
import { CameraFleetCard } from '@/components/CameraFleetCard'
import { BarChart, type BarChartDatum } from '@/components/charts/BarChart'
import { listCameras, getAnalytics, listCameraObjects } from '@/lib/api'
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

interface DashboardViewProps {
  onNavigateToEvents?: () => void
  onNavigateToAnalytics?: () => void
}

export function DashboardView({ onNavigateToEvents, onNavigateToAnalytics }: DashboardViewProps) {
  const [cameras, setCameras] = useState<Camera[]>([])
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null)
  const [camerasError, setCamerasError] = useState<string | null>(null)

  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null)
  const [cameraObjects, setCameraObjects] = useState<TrackedObjectSummary[]>([])
  const [analyticsError, setAnalyticsError] = useState<string | null>(null)

  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)
  const [seekRequest, setSeekRequest] = useState<SeekRequest | null>(null)

  // 1. Fetch camera fleet
  useEffect(() => {
    listCameras()
      .then((result) => {
        setCameras(result)
        setSelectedCameraId((current) => current ?? result[0]?.camera_id ?? null)
      })
      .catch((err: unknown) => setCamerasError(String(err)))
  }, [])

  // 2. Fetch active camera scene (video, trajectories, events, zones, lines)
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
  const error = camerasError ?? sceneError ?? analyticsError

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

      {/* KPI Section — 4 Cards Row */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard
          label="Active Cameras"
          value={cameras.length > 0 ? `${cameras.length} Online` : '0'}
          hint={cameras.length > 0 ? 'All feeds operational' : 'No camera connected'}
        />

        <StatCard
          label="Objects Tracked"
          value={String(trackedCount)}
          hint="Across active camera"
        />

        <StatCard
          label="Events Logged"
          value={String(totalEventsCount)}
          hint={violationCount > 0 ? `${violationCount} violation${violationCount === 1 ? '' : 's'}` : '0 violations'}
          variant={violationCount > 0 ? 'danger' : 'default'}
        />

        <StatCard
          label="Pipeline Status"
          value="Real-time"
          hint="Hardware accelerated"
        />
      </div>

      {/* Primary Operations Section: Live Feed (68%) + Recent Events (32%) */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 items-start">
        {/* Left Column: Live Video Feed Card */}
        <div className="lg:col-span-8 flex flex-col gap-2">
          <Card className="border-border bg-surface shadow-2xs overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between border-b border-border/50 px-4 py-2.5">
              <div className="flex items-center gap-2">
                <CardTitle className="text-sm font-semibold tracking-tight text-primary flex items-center gap-1.5">
                  <Video className="h-4 w-4 text-secondary" />
                  Live Monitoring
                </CardTitle>
                <span className="rounded bg-surface-alt px-1.5 py-0.2 text-[10px] font-mono text-secondary">
                  {selectedCamera?.name ?? selectedCameraId ?? 'No Feed'}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1 rounded-full border border-success/30 bg-success/10 px-2 py-0.2 text-[10px] font-medium text-success">
                  <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
                  Online
                </span>
              </div>
            </CardHeader>

            <CardContent className="p-3">
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
                <div className="flex flex-col items-center justify-center p-12 text-center rounded-lg border border-dashed border-border bg-surface-alt/30 min-h-[300px]">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-alt text-secondary mb-3">
                    <Video className="h-5 w-5" />
                  </div>
                  <p className="text-sm font-semibold text-primary">No video available for this camera</p>
                  <p className="text-xs text-secondary mt-1">
                    Select an active camera or register a video stream to begin monitoring.
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
        <Card className="border-border bg-surface shadow-2xs">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border/50 px-4 py-2.5">
            <CardTitle className="text-xs font-semibold tracking-tight text-primary flex items-center gap-1.5">
              <PieChart className="h-3.5 w-3.5 text-secondary" />
              Object Distribution
            </CardTitle>
            <span className="text-[10px] font-mono text-secondary">
              {perClassObjectData.length} classes
            </span>
          </CardHeader>
          <CardContent className="p-3.5">
            <BarChart
              data={perClassObjectData}
              emptyMessage="No object classifications available yet."
            />
          </CardContent>
        </Card>

        {/* Card B: Event Frequency */}
        <Card className="border-border bg-surface shadow-2xs">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border/50 px-4 py-2.5">
            <CardTitle className="text-xs font-semibold tracking-tight text-primary flex items-center gap-1.5">
              <BarChart3 className="h-3.5 w-3.5 text-secondary" />
              Event Breakdown
            </CardTitle>
            {onNavigateToAnalytics ? (
              <Button
                type="button"
                variant="ghost"
                size="xs"
                onClick={onNavigateToAnalytics}
                className="text-[10px] text-secondary hover:text-primary gap-0.5 h-5 px-1.5"
              >
                <span>Details</span>
                <ChevronRight className="h-3 w-3" />
              </Button>
            ) : (
              <span className="text-[10px] font-mono text-secondary">
                {eventFrequencyData.length} types
              </span>
            )}
          </CardHeader>
          <CardContent className="p-3.5">
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
          onSelectCamera={(id) => setSelectedCameraId(id)}
        />
      </div>
    </div>
  )
}
