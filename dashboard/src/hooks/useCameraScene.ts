import { useEffect, useState } from 'react'
import {
  getObjectTrajectory,
  listCameraEvents,
  listCameraLines,
  listCameraObjects,
  listCameraZones,
  listVideos,
} from '@/lib/api'
import type { Line, TraceEvent, Trajectory, Video, Zone } from '@/lib/api'

export interface CameraScene {
  video: Video | null
  trajectories: Trajectory[]
  events: TraceEvent[]
  zones: Zone[]
  lines: Line[]
  error: string | null
}

/**
 * Fetches everything VideoPlayer/VideoOverlay need to render one camera's
 * current video (its video record, every tracked object's trajectory, all
 * events, zones, lines) -- extracted in Phase 10.3 from LiveView (Phase
 * 10.1) so EventsView can reuse the exact same fetch-and-assemble logic
 * instead of duplicating it. `events` here is always the camera's full,
 * unfiltered event list (needed for accurate overlay violation-state
 * rendering regardless of what an events table elsewhere is filtered to).
 */
export function useCameraScene(cameraId: string | null): CameraScene {
  const [video, setVideo] = useState<Video | null>(null)
  const [trajectories, setTrajectories] = useState<Trajectory[]>([])
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [zones, setZones] = useState<Zone[]>([])
  const [lines, setLines] = useState<Line[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!cameraId) return
    let cancelled = false
    setError(null)
    setVideo(null)
    setTrajectories([])
    setEvents([])
    setZones([])
    setLines([])

    Promise.all([
      listVideos(cameraId),
      listCameraObjects(cameraId),
      listCameraEvents(cameraId),
      listCameraZones(cameraId),
      listCameraLines(cameraId),
    ])
      .then(async ([videos, objects, cameraEvents, cameraZones, cameraLines]) => {
        if (cancelled) return
        setVideo(videos[0] ?? null)
        setEvents(cameraEvents)
        setZones(cameraZones)
        setLines(cameraLines)
        const trajectoryList = await Promise.all(objects.map((object) => getObjectTrajectory(object.id)))
        if (!cancelled) setTrajectories(trajectoryList)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(String(err))
      })

    return () => {
      cancelled = true
    }
  }, [cameraId])

  return { video, trajectories, events, zones, lines, error }
}
