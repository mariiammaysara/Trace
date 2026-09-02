import { useEffect, useState } from 'react'
import { StatCard } from '@/components/StatCard'
import { EventBadge } from '@/components/EventBadge'
import { VideoPlayer } from '@/components/VideoPlayer'
import { useCameraScene } from '@/hooks/useCameraScene'
import { getObjectEvents, getObjectProfile } from '@/lib/api'
import type { ObjectProfile, TraceEvent } from '@/lib/api'
import { formatSeconds } from '@/lib/analytics'
import { cn } from '@/lib/utils'
import { X, Video, Clock, Route } from 'lucide-react'

interface ObjectProfilePanelProps {
  objectId: number | null
  onClose: () => void
  /** Opens Phase 18's incident view for one of this object's own events --
   * the panel only knows the event id and this object's camera, App.tsx
   * owns actually switching views/cameras. */
  onOpenIncident: (eventId: number, cameraId: string) => void
}

/**
 * Phase 19's Object Profile view: everything TRACE already knows about one
 * tracked object, opened by clicking its `#object_id` from anywhere in the
 * dashboard (video overlay, event list, incident view). Every field is a
 * real stored column or a real server-side aggregate over stored rows
 * (GET /objects/{id}) -- no new tracking logic runs here, this is purely
 * presentation. Trajectory/video rendering reuses VideoPlayer/VideoOverlay
 * verbatim (Phase 10.1), scoped to just this one object's own trajectory
 * and events so the overlay isn't cluttered with unrelated tracks.
 */
export function ObjectProfilePanel({ objectId, onClose, onOpenIncident }: ObjectProfilePanelProps) {
  const [profile, setProfile] = useState<ObjectProfile | null>(null)
  const [ownEvents, setOwnEvents] = useState<TraceEvent[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (objectId === null) {
      setProfile(null)
      setOwnEvents([])
      setError(null)
      return
    }
    let cancelled = false
    setError(null)
    setProfile(null)

    Promise.all([getObjectProfile(objectId), getObjectEvents(objectId)])
      .then(([profileResult, eventsResult]) => {
        if (cancelled) return
        setProfile(profileResult)
        setOwnEvents(eventsResult)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(String(err))
      })

    return () => {
      cancelled = true
    }
  }, [objectId])

  // Reuses the exact same camera-scene fetch LiveView/EventsView use
  // (Phase 10.3) -- only the video/zones/lines are needed from it; the
  // object's own trajectory is picked out below so the overlay renders
  // just this object, not the whole camera's traffic.
  const { video, trajectories, zones, lines, error: sceneError } = useCameraScene(profile?.camera_id ?? null)
  const ownTrajectory = profile ? trajectories.find((t) => t.object_id === profile.id) : undefined

  const open = objectId !== null

  return (
    <div
      aria-hidden={!open}
      className={cn(
        'fixed inset-0 z-40 flex justify-end transition-[visibility]',
        open ? 'visible' : 'invisible pointer-events-none',
      )}
    >
      <div
        onClick={onClose}
        className={cn(
          'absolute inset-0 bg-primary/50 backdrop-blur-xs transition-opacity',
          open ? 'opacity-100' : 'opacity-0',
        )}
      />

      <div
        role="dialog"
        aria-label={profile ? `Object #${profile.id} profile` : 'Object profile'}
        className={cn(
          'relative flex h-full w-full max-w-xl flex-col overflow-y-auto border-l border-border bg-background shadow-2xl transition-transform',
          open ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold text-ink">
            {profile ? (
              <>
                Object #{profile.id} <span className="text-ink-subtle font-normal">· {profile.class_name}</span>
              </>
            ) : (
              'Object profile'
            )}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close object profile"
            className="rounded p-1 text-ink-subtle hover:bg-surface-alt hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex flex-col gap-4 p-4">
          {(error ?? sceneError) && (
            <div role="alert" className="rounded-md border border-danger bg-danger/10 px-4 py-2 text-sm text-danger">
              {error ?? sceneError}
            </div>
          )}

          {!profile && !error ? (
            <p className="text-sm text-ink-subtle">Loading object profile…</p>
          ) : profile ? (
            <>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-lg border border-border bg-surface px-3.5 py-2.5 text-xs">
                <span className="flex items-center gap-1 text-ink-subtle">
                  <Video className="h-3 w-3" />
                  {profile.camera_name ?? profile.camera_id}
                </span>
                <span className="flex items-center gap-1 font-mono text-ink-subtle tabular-nums">
                  <Clock className="h-3 w-3" />
                  first {profile.first_seen.toFixed(1)}s · last {profile.last_seen.toFixed(1)}s
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <StatCard label="Total dwell time" value={formatSeconds(profile.total_dwell_seconds)} />
                <StatCard label="Event count" value={String(profile.event_count)} />
              </div>

              {ownTrajectory && video && (
                <div className="flex flex-col gap-1.5">
                  <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-quiet">
                    <Route className="h-3 w-3" />
                    Trajectory ({ownTrajectory.points.length} points)
                  </span>
                  <VideoPlayer
                    video={video}
                    trajectories={[ownTrajectory]}
                    events={ownEvents}
                    zones={zones}
                    lines={lines}
                    cameraName={profile.camera_name ?? profile.camera_id}
                  />
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold uppercase tracking-wide text-ink-quiet">
                  Events ({ownEvents.length})
                </span>
                <div className="flex flex-col divide-y divide-border/40 rounded-lg border border-border bg-surface">
                  {ownEvents.length === 0 ? (
                    <p className="p-3 text-xs text-ink-subtle">No events stored for this object.</p>
                  ) : (
                    ownEvents.map((event) => (
                      <button
                        key={event.id}
                        type="button"
                        onClick={() => onOpenIncident(event.id, profile.camera_id)}
                        className="flex items-center justify-between gap-2 px-3 py-2 text-left text-xs hover:bg-surface-alt/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent"
                      >
                        <span className="flex items-center gap-1.5">
                          <EventBadge eventType={event.event_type} />
                          <span className="font-mono text-ink-subtle tabular-nums">{event.timestamp.toFixed(1)}s</span>
                        </span>
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-accent">
                          Open incident
                        </span>
                      </button>
                    ))
                  )}
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
