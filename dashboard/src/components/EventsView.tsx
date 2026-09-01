import { useEffect, useState, type KeyboardEvent } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { EventBadge } from '@/components/EventBadge'
import { VideoPlayer, type SeekRequest } from '@/components/VideoPlayer'
import { listCameras, listCameraEvents } from '@/lib/api'
import type { Camera, TraceEvent } from '@/lib/api'
import { useCameraScene } from '@/hooks/useCameraScene'
import { ALL_EVENT_TYPES } from '@/lib/eventSeverity'
import { cn } from '@/lib/utils'

const ALL_TYPES_VALUE = 'all'

/**
 * Event Investigation view: a filterable event table that, on row click,
 * jumps the shared VideoPlayer to that event's timestamp -- the
 * event -> timestamp -> video segment -> relevant frame flow (Section 0).
 * The table's own event fetch is filtered server-side (GET
 * /cameras/{id}/events?event_type=&start_time=&end_time=); the player and
 * its overlay always see the camera's full, unfiltered event list (via
 * useCameraScene) so violation-state rendering stays accurate regardless of
 * what the table is currently filtered to. No mock/hardcoded data.
 */
export function EventsView() {
  const [cameras, setCameras] = useState<Camera[]>([])
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null)
  const [camerasError, setCamerasError] = useState<string | null>(null)

  const [eventTypeFilter, setEventTypeFilter] = useState<string>(ALL_TYPES_VALUE)
  const [startTimeInput, setStartTimeInput] = useState('')
  const [endTimeInput, setEndTimeInput] = useState('')

  const [filteredEvents, setFilteredEvents] = useState<TraceEvent[]>([])
  const [filterError, setFilterError] = useState<string | null>(null)

  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)
  const [seekRequest, setSeekRequest] = useState<SeekRequest | null>(null)

  useEffect(() => {
    listCameras()
      .then((result) => {
        setCameras(result)
        setSelectedCameraId((current) => current ?? result[0]?.camera_id ?? null)
      })
      .catch((err: unknown) => setCamerasError(String(err)))
  }, [])

  const { video, trajectories, events, zones, lines, error: sceneError } = useCameraScene(selectedCameraId)

  const startTime = startTimeInput.trim() === '' ? undefined : Number(startTimeInput)
  const endTime = endTimeInput.trim() === '' ? undefined : Number(endTimeInput)

  useEffect(() => {
    if (!selectedCameraId) return
    let cancelled = false
    setFilterError(null)

    listCameraEvents(selectedCameraId, {
      eventType: eventTypeFilter === ALL_TYPES_VALUE ? undefined : eventTypeFilter,
      startTime: Number.isFinite(startTime) ? startTime : undefined,
      endTime: Number.isFinite(endTime) ? endTime : undefined,
    })
      .then((result) => {
        if (!cancelled) setFilteredEvents(result)
      })
      .catch((err: unknown) => {
        if (!cancelled) setFilterError(String(err))
      })

    return () => {
      cancelled = true
    }
  }, [selectedCameraId, eventTypeFilter, startTime, endTime])

  function handleRowClick(event: TraceEvent) {
    setSelectedEventId(event.id)
    setSeekRequest({ time: event.timestamp, nonce: Date.now() })
  }

  function handleRowKeyDown(event: KeyboardEvent, traceEvent: TraceEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      handleRowClick(traceEvent)
    }
  }

  function clearFilters() {
    setEventTypeFilter(ALL_TYPES_VALUE)
    setStartTimeInput('')
    setEndTimeInput('')
  }

  const error = camerasError ?? sceneError ?? filterError

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-primary">Events</h1>
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

      {video && (
        <VideoPlayer video={video} trajectories={trajectories} events={events} zones={zones} lines={lines} seekRequest={seekRequest} />
      )}

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3">
        <div className="flex flex-col gap-1">
          <label htmlFor="event-type-filter" className="text-xs font-medium uppercase tracking-wide text-secondary">
            Event type
          </label>
          <Select value={eventTypeFilter} onValueChange={(value) => setEventTypeFilter(value ?? ALL_TYPES_VALUE)}>
            <SelectTrigger id="event-type-filter" className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_TYPES_VALUE}>All types</SelectItem>
              {ALL_EVENT_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="start-time-filter" className="text-xs font-medium uppercase tracking-wide text-secondary">
            Start (s)
          </label>
          <Input
            id="start-time-filter"
            type="number"
            placeholder="0"
            className="w-24"
            value={startTimeInput}
            onChange={(event) => setStartTimeInput(event.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="end-time-filter" className="text-xs font-medium uppercase tracking-wide text-secondary">
            End (s)
          </label>
          <Input
            id="end-time-filter"
            type="number"
            placeholder="—"
            className="w-24"
            value={endTimeInput}
            onChange={(event) => setEndTimeInput(event.target.value)}
          />
        </div>

        <Button type="button" variant="outline" onClick={clearFilters}>
          Clear filters
        </Button>
      </div>

      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Object</TableHead>
              <TableHead>Class</TableHead>
              <TableHead>Confidence</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEvents.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-secondary">
                  No events match the current filters.
                </TableCell>
              </TableRow>
            )}
            {filteredEvents.map((event) => (
              <TableRow
                key={event.id}
                role="button"
                tabIndex={0}
                aria-selected={event.id === selectedEventId}
                data-state={event.id === selectedEventId ? 'selected' : undefined}
                onClick={() => handleRowClick(event)}
                onKeyDown={(keyEvent) => handleRowKeyDown(keyEvent, event)}
                className={cn(
                  'cursor-pointer outline-none',
                  'focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent',
                )}
              >
                <TableCell className="tabular-nums text-secondary">{event.timestamp.toFixed(1)}s</TableCell>
                <TableCell>
                  <EventBadge eventType={event.event_type} />
                </TableCell>
                <TableCell>#{event.object_id}</TableCell>
                <TableCell>{event.class_name}</TableCell>
                <TableCell className="tabular-nums">{Math.round(event.confidence * 100)}%</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
