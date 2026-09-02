import { useEffect, useState, type KeyboardEvent } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { EventBadge } from '@/components/EventBadge'
import { VideoPlayer, type SeekRequest } from '@/components/VideoPlayer'
import { listCameraEvents, getObjectTrajectory } from '@/lib/api'
import type { Camera, TraceEvent, Trajectory } from '@/lib/api'
import { useCameraScene } from '@/hooks/useCameraScene'
import { ALL_EVENT_TYPES, classifyEventSeverity } from '@/lib/eventSeverity'
import { cn } from '@/lib/utils'
import { Clock, Layers, Route, Link2, Search } from 'lucide-react'

const ALL_TYPES_VALUE = 'all'

const SEVERITY_BORDER: Record<string, string> = {
  danger: 'border-l-danger',
  warning: 'border-l-warning',
  info: 'border-l-transparent',
}

interface EventsViewProps {
  cameras: Camera[]
  selectedCameraId: string | null
  onSelectCamera: (cameraId: string | null) => void
  /** 'events': scannable filtered log with seek-to-play. 'investigation':
   * EVENT -> TIMESTAMP -> EVIDENCE -> OBJECT -> TRAJECTORY -> RELATED EVENTS
   * workspace built around one selected event (Phase 10.3 / Section 0). */
  mode?: 'events' | 'investigation'
}

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
export function EventsView({ cameras, selectedCameraId, onSelectCamera, mode = 'events' }: EventsViewProps) {
  const [eventTypeFilter, setEventTypeFilter] = useState<string>(ALL_TYPES_VALUE)
  const [startTimeInput, setStartTimeInput] = useState('')
  const [endTimeInput, setEndTimeInput] = useState('')

  const [filteredEvents, setFilteredEvents] = useState<TraceEvent[]>([])
  const [filterError, setFilterError] = useState<string | null>(null)

  const [selectedEventId, setSelectedEventId] = useState<number | null>(null)
  const [seekRequest, setSeekRequest] = useState<SeekRequest | null>(null)

  const [trajectory, setTrajectory] = useState<Trajectory | null>(null)
  const [trajectoryError, setTrajectoryError] = useState<string | null>(null)

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

  // Reset selection when the camera changes -- a selected event from another
  // camera's event list is meaningless once the scene switches under it.
  useEffect(() => {
    setSelectedEventId(null)
    setTrajectory(null)
  }, [selectedCameraId])

  const selectedEvent = events.find((event) => event.id === selectedEventId) ?? null

  useEffect(() => {
    if (!selectedEvent || mode !== 'investigation') {
      setTrajectory(null)
      return
    }
    let cancelled = false
    setTrajectoryError(null)
    getObjectTrajectory(selectedEvent.object_id)
      .then((result) => {
        if (!cancelled) setTrajectory(result)
      })
      .catch((err: unknown) => {
        if (!cancelled) setTrajectoryError(String(err))
      })
    return () => {
      cancelled = true
    }
  }, [selectedEvent, mode])

  function handleSelectEvent(event: TraceEvent) {
    setSelectedEventId(event.id)
    setSeekRequest({ time: event.timestamp, nonce: Date.now() })
  }

  function handleRowKeyDown(event: KeyboardEvent, traceEvent: TraceEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      handleSelectEvent(traceEvent)
    }
  }

  function clearFilters() {
    setEventTypeFilter(ALL_TYPES_VALUE)
    setStartTimeInput('')
    setEndTimeInput('')
  }

  const error = sceneError ?? filterError

  const cameraSelector = (
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
  )

  const filterBar = (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-surface p-3">
      <div className="flex flex-col gap-1">
        <label htmlFor="event-type-filter" className="text-xs font-semibold uppercase tracking-wide text-ink-quiet">
          Event type
        </label>
        <Select value={eventTypeFilter} onValueChange={(value) => setEventTypeFilter(value ?? ALL_TYPES_VALUE)}>
          <SelectTrigger id="event-type-filter" className="w-44">
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
        <label htmlFor="start-time-filter" className="text-xs font-semibold uppercase tracking-wide text-ink-quiet">
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
        <label htmlFor="end-time-filter" className="text-xs font-semibold uppercase tracking-wide text-ink-quiet">
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
  )

  if (mode === 'investigation') {
    const relatedEvents = selectedEvent
      ? events
          .filter((event) => event.object_id === selectedEvent.object_id && event.id !== selectedEvent.id)
          .sort((a, b) => a.timestamp - b.timestamp)
      : []

    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-end">{cameraSelector}</div>
        {error && (
          <div role="alert" className="rounded-md border border-danger bg-danger/10 px-4 py-2 text-sm text-danger">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-12 items-start">
          {/* Event picker */}
          <div className="lg:col-span-4 flex flex-col gap-3">
            {filterBar}
            <Card className="border-border bg-surface shadow-2xs">
              <CardContent className="p-0 max-h-[560px] overflow-y-auto divide-y divide-border/40">
                {filteredEvents.length === 0 ? (
                  <p className="p-4 text-xs text-ink-subtle text-center">No events match the current filters.</p>
                ) : (
                  filteredEvents.map((event) => {
                    const severity = classifyEventSeverity(event.event_type)
                    const isSelected = event.id === selectedEventId
                    return (
                      <div
                        key={event.id}
                        role="button"
                        tabIndex={0}
                        onClick={() => handleSelectEvent(event)}
                        onKeyDown={(keyEvent) => handleRowKeyDown(keyEvent, event)}
                        className={cn(
                          'flex items-center justify-between gap-2 px-3.5 py-2.5 cursor-pointer select-none border-l-2 transition-colors',
                          'hover:bg-surface-alt/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent',
                          isSelected ? 'bg-accent/10 border-l-accent' : SEVERITY_BORDER[severity],
                        )}
                      >
                        <div className="flex flex-col gap-0.5 min-w-0">
                          <div className="flex items-center gap-1.5">
                            <EventBadge eventType={event.event_type} />
                            <span className="text-xs font-mono font-medium text-ink">#{event.object_id}</span>
                          </div>
                          <span className="flex items-center gap-1 text-[11px] text-ink-subtle font-mono tabular-nums">
                            <Clock className="h-2.5 w-2.5" />
                            {event.timestamp.toFixed(1)}s
                          </span>
                        </div>
                        <span className="text-[10px] font-mono text-ink-subtle tabular-nums shrink-0">
                          {Math.round(event.confidence * 100)}%
                        </span>
                      </div>
                    )
                  })
                )}
              </CardContent>
            </Card>
          </div>

          {/* Evidence workspace */}
          <div className="lg:col-span-8 flex flex-col gap-3">
            {!selectedEvent ? (
              <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-surface-alt/30 p-16 text-center">
                <Search className="h-8 w-8 text-ink-subtle" />
                <p className="text-sm font-semibold text-ink">Select an event to begin investigating</p>
                <p className="text-xs text-ink-subtle max-w-xs">
                  Pick an event from the list to see its evidence, tracked object, and trajectory.
                </p>
              </div>
            ) : (
              <>
                <Card className="border-accent/40 bg-surface shadow-2xs">
                  <CardContent className="flex flex-wrap items-center gap-x-6 gap-y-2">
                    <div className="flex items-center gap-2">
                      <EventBadge eventType={selectedEvent.event_type} />
                      <span className="text-sm font-semibold text-ink">
                        #{selectedEvent.object_id} {selectedEvent.class_name}
                      </span>
                    </div>
                    <span className="flex items-center gap-1 text-xs font-mono text-ink-subtle tabular-nums">
                      <Clock className="h-3 w-3" />
                      {selectedEvent.timestamp.toFixed(1)}s
                    </span>
                    <span className="text-xs font-mono text-ink-subtle tabular-nums">
                      {Math.round(selectedEvent.confidence * 100)}% confidence
                    </span>
                    {selectedEvent.zone_id && (
                      <span className="rounded bg-surface-alt px-1.5 py-0.5 text-[10px] font-mono text-ink-subtle">
                        zone: {selectedEvent.zone_id}
                      </span>
                    )}
                    {selectedEvent.line_id && (
                      <span className="rounded bg-surface-alt px-1.5 py-0.5 text-[10px] font-mono text-ink-subtle">
                        line: {selectedEvent.line_id}
                      </span>
                    )}
                    {typeof selectedEvent.metadata?.speed === 'number' && (
                      <span className="font-mono text-danger font-semibold text-xs">
                        {Math.round(selectedEvent.metadata.speed as number)} km/h
                      </span>
                    )}
                  </CardContent>
                </Card>

                {video && (
                  <VideoPlayer
                    video={video}
                    trajectories={trajectories}
                    events={events}
                    zones={zones}
                    lines={lines}
                    seekRequest={seekRequest}
                  />
                )}

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <Card size="sm" className="border-border bg-surface shadow-2xs">
                    <CardHeader className="flex flex-row items-center gap-1.5 border-b border-border/50">
                      <Route className="h-3.5 w-3.5 text-ink-subtle" />
                      <CardTitle className="text-xs font-semibold tracking-tight text-ink">Trajectory</CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-1.5 text-xs">
                      {trajectoryError && <p className="text-danger">{trajectoryError}</p>}
                      {!trajectoryError && trajectory && (
                        <>
                          <div className="flex items-center justify-between">
                            <span className="text-ink-subtle">Tracked points</span>
                            <span className="font-mono tabular-nums text-ink">{trajectory.points.length}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-ink-subtle">First seen</span>
                            <span className="font-mono tabular-nums text-ink">{trajectory.first_seen.toFixed(1)}s</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-ink-subtle">Last seen</span>
                            <span className="font-mono tabular-nums text-ink">{trajectory.last_seen.toFixed(1)}s</span>
                          </div>
                        </>
                      )}
                      {!trajectoryError && !trajectory && <p className="text-ink-subtle">Loading trajectory…</p>}
                    </CardContent>
                  </Card>

                  <Card size="sm" className="border-border bg-surface shadow-2xs">
                    <CardHeader className="flex flex-row items-center gap-1.5 border-b border-border/50">
                      <Link2 className="h-3.5 w-3.5 text-ink-subtle" />
                      <CardTitle className="text-xs font-semibold tracking-tight text-ink">
                        Related events
                      </CardTitle>
                      <span className="ml-auto text-[10px] font-mono text-ink-subtle">{relatedEvents.length}</span>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-1.5 max-h-[140px] overflow-y-auto">
                      {relatedEvents.length === 0 ? (
                        <p className="text-xs text-ink-subtle">No other events for this object.</p>
                      ) : (
                        relatedEvents.map((event) => (
                          <button
                            key={event.id}
                            type="button"
                            onClick={() => handleSelectEvent(event)}
                            className="flex items-center justify-between gap-2 rounded px-1.5 py-1 text-left text-xs hover:bg-surface-alt/60 focus-visible:outline-2 focus-visible:outline-accent"
                          >
                            <EventBadge eventType={event.event_type} />
                            <span className="font-mono text-ink-subtle tabular-nums">{event.timestamp.toFixed(1)}s</span>
                          </button>
                        ))
                      )}
                    </CardContent>
                  </Card>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-end">{cameraSelector}</div>

      {error && (
        <div role="alert" className="rounded-md border border-danger bg-danger/10 px-4 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      {video && (
        <VideoPlayer video={video} trajectories={trajectories} events={events} zones={zones} lines={lines} seekRequest={seekRequest} />
      )}

      {filterBar}

      <Card size="sm" className="border-border bg-surface shadow-2xs overflow-hidden">
        <CardHeader className="flex flex-row items-center gap-1.5 border-b border-border/50">
          <Layers className="h-3.5 w-3.5 text-ink-subtle" />
          <CardTitle className="text-xs font-semibold tracking-tight text-ink">Event log</CardTitle>
          <span className="ml-auto text-[10px] font-mono text-ink-subtle">{filteredEvents.length} events</span>
        </CardHeader>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-20">Time</TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="w-16">Object</TableHead>
              <TableHead>Class</TableHead>
              <TableHead className="w-24 text-right">Confidence</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredEvents.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-ink-subtle py-6">
                  No events match the current filters.
                </TableCell>
              </TableRow>
            )}
            {filteredEvents.map((event) => {
              const severity = classifyEventSeverity(event.event_type)
              return (
                <TableRow
                  key={event.id}
                  role="button"
                  tabIndex={0}
                  aria-selected={event.id === selectedEventId}
                  data-state={event.id === selectedEventId ? 'selected' : undefined}
                  onClick={() => handleSelectEvent(event)}
                  onKeyDown={(keyEvent) => handleRowKeyDown(keyEvent, event)}
                  className={cn(
                    'cursor-pointer outline-none border-l-2',
                    SEVERITY_BORDER[severity],
                    'focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent',
                  )}
                >
                  <TableCell className="tabular-nums text-ink-subtle font-mono">{event.timestamp.toFixed(1)}s</TableCell>
                  <TableCell>
                    <EventBadge eventType={event.event_type} />
                  </TableCell>
                  <TableCell className="font-mono">#{event.object_id}</TableCell>
                  <TableCell>{event.class_name}</TableCell>
                  <TableCell className="tabular-nums text-right font-mono">{Math.round(event.confidence * 100)}%</TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
