import { useEffect, useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart, type BarChartDatum } from '@/components/charts/BarChart'
import { getAnalytics, listCameraEvents } from '@/lib/api'
import type { AnalyticsSummary, Camera, TraceEvent } from '@/lib/api'
import { classifyEventType } from '@/lib/eventClassification'
import { computeBusiestHours, formatHourLabel, formatSeconds } from '@/lib/analytics'
import { BarChart3, PieChart, Clock3 } from 'lucide-react'

interface AnalyticsViewProps {
  cameras: Camera[]
  selectedCameraId: string | null
  onSelectCamera: (cameraId: string | null) => void
}

/**
 * The Analytics dashboard view: every number and chart comes from real
 * Section 11 queries via GET /analytics, plus GET /cameras/{id}/events for
 * busiest_hours (omitted from the /analytics bundle -- see
 * src/lib/api.ts#getAnalytics). Nothing here is mock/hardcoded data.
 */
export function AnalyticsView({ cameras, selectedCameraId, onSelectCamera }: AnalyticsViewProps) {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null)
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [error, setError] = useState<string | null>(null)

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

  const busiestHours = computeBusiestHours(events)
  const nonZeroHours = busiestHours.filter((h) => h.count > 0).length
  const hasTemporalSpread = nonZeroHours > 1

  const busiestHoursData: BarChartDatum[] = busiestHours.map(({ hour, count }) => ({
    key: String(hour),
    label: formatHourLabel(hour).slice(0, 2),
    value: count,
    variant: 'accent',
    title: `${formatHourLabel(hour)} — ${count} event${count === 1 ? '' : 's'}`,
  }))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-end">
        <Select value={selectedCameraId} onValueChange={(value) => onSelectCamera(value)}>
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
          {/* Supporting numbers -- one dense strip, not five separate cards. */}
          <div className="flex flex-wrap items-center divide-x divide-border rounded-md border border-border bg-surface">
            <div className="flex items-center gap-1.5 px-3.5 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Objects tracked</span>
              <span data-testid="metric-objects-tracked" className="font-mono text-sm font-semibold text-ink">{analytics.object_count}</span>
            </div>
            <div className="flex items-center gap-1.5 px-3.5 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Line crossings</span>
              <span data-testid="metric-line-crossings" className="font-mono text-sm font-semibold text-ink">{analytics.line_crossing_count}</span>
            </div>
            <div className="flex items-center gap-1.5 px-3.5 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Zone violations</span>
              <span
                data-testid="metric-zone-violations"
                className={`font-mono text-sm font-semibold ${analytics.zone_violation_count > 0 ? 'text-danger' : 'text-ink'}`}
              >
                {analytics.zone_violation_count}
              </span>
            </div>
            <div className="flex items-center gap-1.5 px-3.5 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Traffic volume</span>
              <span data-testid="metric-traffic-volume" className="font-mono text-sm font-semibold text-ink">{analytics.traffic_volume}</span>
            </div>
            <div className="flex items-center gap-1.5 px-3.5 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Avg. dwell</span>
              <span data-testid="metric-avg-dwell" className="font-mono text-sm font-semibold text-ink">{formatSeconds(analytics.average_dwell_time)}</span>
            </div>
          </div>

          {/* Primary insight: what's happening, by type -- gets the most
              width. Secondary: composition by class. Both real event/object
              data from the same GET /analytics response. */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
            <Card size="sm" className="lg:col-span-3 border-border bg-surface shadow-2xs">
              <CardHeader className="flex flex-row items-center gap-1.5 border-b border-border/50">
                <BarChart3 className="h-3.5 w-3.5 text-ink-subtle" />
                <CardTitle className="text-xs font-semibold tracking-tight text-ink">Event frequency</CardTitle>
                <span className="ml-auto text-[10px] text-ink-subtle">what's happening, by type</span>
              </CardHeader>
              <CardContent>
                <BarChart data={eventFrequencyData} emptyMessage="No events recorded yet for this camera." />
              </CardContent>
            </Card>

            <Card size="sm" className="lg:col-span-2 border-border bg-surface shadow-2xs">
              <CardHeader className="flex flex-row items-center gap-1.5 border-b border-border/50">
                <PieChart className="h-3.5 w-3.5 text-ink-subtle" />
                <CardTitle className="text-xs font-semibold tracking-tight text-ink">Per-class stats</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div>
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-ink-quiet">Objects tracked</p>
                  <BarChart data={perClassObjectData} emptyMessage="No objects tracked yet." />
                </div>
                <div>
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-ink-quiet">Events</p>
                  <BarChart data={perClassEventData} emptyMessage="No events recorded yet." />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Supporting detail: temporal pattern. Deliberately does not
              render the full 24-slot chart when the data can't actually
              support it (see src/lib/analytics.ts's documented UTC-bucketing
              caveat for file-based sources) -- a wall of empty hour slots
              isn't insight, it's noise. */}
          <Card size="sm" className="border-border bg-surface shadow-2xs">
            <CardHeader className="flex flex-row items-center gap-1.5 border-b border-border/50">
              <Clock3 className="h-3.5 w-3.5 text-ink-subtle" />
              <CardTitle className="text-xs font-semibold tracking-tight text-ink">Busiest hours</CardTitle>
            </CardHeader>
            <CardContent>
              {hasTemporalSpread ? (
                <>
                  <BarChart data={busiestHoursData} orientation="vertical" />
                  <p className="mt-3 text-xs text-ink-subtle">
                    Hour-of-day is derived from each event's timestamp treated as Unix epoch seconds (UTC).
                  </p>
                </>
              ) : (
                <p className="text-xs text-ink-subtle">
                  {events.length === 0
                    ? 'No events recorded yet for this camera.'
                    : `Not enough time-of-day spread to plot yet -- all ${events.length} event${events.length === 1 ? '' : 's'} fall in the same UTC hour. File-based sources use video-relative timestamps rather than real capture time (see TRACE_STUDY_GUIDE.md Section 11), so this chart stays limited until events come from a live-camera source.`}
                </p>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {!analytics && !error && <p className="text-ink-subtle">Loading analytics…</p>}
    </div>
  )
}
