import { useEffect, useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatCard } from '@/components/StatCard'
import { BarChart, type BarChartDatum } from '@/components/charts/BarChart'
import { getAnalytics, listCameraEvents, listCameras } from '@/lib/api'
import type { AnalyticsSummary, Camera, TraceEvent } from '@/lib/api'
import { classifyEventType } from '@/lib/eventClassification'
import { computeBusiestHours, formatHourLabel, formatSeconds } from '@/lib/analytics'

/**
 * The Analytics dashboard view: every number and chart comes from real
 * Section 11 queries via GET /analytics, plus GET /cameras/{id}/events for
 * busiest_hours (omitted from the /analytics bundle -- see
 * src/lib/api.ts#getAnalytics). Nothing here is mock/hardcoded data.
 */
export function AnalyticsView() {
  const [cameras, setCameras] = useState<Camera[]>([])
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null)
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null)
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listCameras()
      .then((result) => {
        setCameras(result)
        setSelectedCameraId((current) => current ?? result[0]?.camera_id ?? null)
      })
      .catch((err: unknown) => setError(String(err)))
  }, [])

  useEffect(() => {
    if (!selectedCameraId) return
    let cancelled = false
    setError(null)

    Promise.all([getAnalytics(selectedCameraId), listCameraEvents(selectedCameraId)])
      .then(([summary, cameraEvents]) => {
        if (cancelled) return
        setAnalytics(summary)
        setEvents(cameraEvents)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(String(err))
      })

    return () => {
      cancelled = true
    }
  }, [selectedCameraId])

  const eventFrequencyData: BarChartDatum[] = analytics
    ? Object.entries(analytics.event_frequency)
        .sort((a, b) => b[1] - a[1])
        .map(([eventType, count]) => ({
          key: eventType,
          label: eventType,
          value: count,
          variant: classifyEventType(eventType),
        }))
    : []

  const perClassObjectData: BarChartDatum[] = analytics
    ? Object.entries(analytics.per_class_stats)
        .sort((a, b) => b[1].object_count - a[1].object_count)
        .map(([className, stats]) => ({
          key: className,
          label: className,
          value: stats.object_count,
          variant: 'secondary',
        }))
    : []

  const perClassEventData: BarChartDatum[] = analytics
    ? Object.entries(analytics.per_class_stats)
        .sort((a, b) => b[1].event_count - a[1].event_count)
        .map(([className, stats]) => ({
          key: className,
          label: className,
          value: stats.event_count,
          variant: 'accent',
        }))
    : []

  const busiestHoursData: BarChartDatum[] = computeBusiestHours(events).map(({ hour, count }) => ({
    key: String(hour),
    label: formatHourLabel(hour).slice(0, 2),
    value: count,
    variant: 'accent',
    title: `${formatHourLabel(hour)} — ${count} event${count === 1 ? '' : 's'}`,
  }))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-primary">Analytics</h1>
        <Select value={selectedCameraId} onValueChange={(value) => setSelectedCameraId(value)}>
          <SelectTrigger className="w-56">
            <SelectValue placeholder="Select a camera" />
          </SelectTrigger>
          <SelectContent>
            {cameras.map((camera) => (
              <SelectItem key={camera.camera_id} value={camera.camera_id}>
                {camera.name ?? camera.camera_id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {error && (
        <div role="alert" className="rounded-md border border-danger bg-danger/10 px-4 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      {analytics && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
            <StatCard label="Objects tracked" value={String(analytics.object_count)} />
            <StatCard label="Line crossings" value={String(analytics.line_crossing_count)} />
            <StatCard label="Zone violations" value={String(analytics.zone_violation_count)} variant="danger" />
            <StatCard label="Traffic volume" value={String(analytics.traffic_volume)} hint="distinct objects through a line" />
            <StatCard label="Avg. dwell time" value={formatSeconds(analytics.average_dwell_time)} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Event frequency</CardTitle>
              </CardHeader>
              <CardContent>
                <BarChart data={eventFrequencyData} emptyMessage="No events recorded yet for this camera." />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Per-class stats</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-secondary">Objects tracked</p>
                  <BarChart data={perClassObjectData} emptyMessage="No objects tracked yet." />
                </div>
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-secondary">Events</p>
                  <BarChart data={perClassEventData} emptyMessage="No events recorded yet." />
                </div>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Busiest hours</CardTitle>
              </CardHeader>
              <CardContent>
                <BarChart data={busiestHoursData} orientation="vertical" />
                <p className="mt-3 text-xs text-secondary">
                  Hour-of-day is derived from each event's timestamp treated as Unix epoch seconds (UTC) — correct for
                  live-camera sources, but file-based sources (like this demo) use video-relative timestamps, so
                  everything currently buckets into 00:00 UTC. See TRACE_STUDY_GUIDE.md Section 11.
                </p>
              </CardContent>
            </Card>
          </div>
        </>
      )}

      {!analytics && !error && <p className="text-secondary">Loading analytics…</p>}
    </div>
  )
}
