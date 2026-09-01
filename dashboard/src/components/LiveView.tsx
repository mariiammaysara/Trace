import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { VideoOverlay } from '@/components/VideoOverlay'
import {
  getObjectTrajectory,
  getVideoStreamUrl,
  listCameraEvents,
  listCameraLines,
  listCameraObjects,
  listCameraZones,
  listCameras,
  listVideos,
} from '@/lib/api'
import type { Camera, Line, TraceEvent, Trajectory, Video, Zone } from '@/lib/api'

/**
 * The Live/Video dashboard view: real video playback with detection boxes,
 * track IDs, trajectories, zones, and lines overlaid via VideoOverlay's SVG
 * layer, synced to playback -- never baked into the video file. Every value
 * shown comes from the Phase 9/10 API (src/lib/api.ts); nothing here is
 * mock/hardcoded data.
 */
export function LiveView() {
  const [cameras, setCameras] = useState<Camera[]>([])
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null)
  const [video, setVideo] = useState<Video | null>(null)
  const [trajectories, setTrajectories] = useState<Trajectory[]>([])
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [zones, setZones] = useState<Zone[]>([])
  const [lines, setLines] = useState<Line[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [videoSize, setVideoSize] = useState({ width: 0, height: 0 })

  const videoRef = useRef<HTMLVideoElement>(null)

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
    setVideo(null)
    setTrajectories([])

    Promise.all([
      listVideos(selectedCameraId),
      listCameraObjects(selectedCameraId),
      listCameraEvents(selectedCameraId),
      listCameraZones(selectedCameraId),
      listCameraLines(selectedCameraId),
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
  }, [selectedCameraId])

  function togglePlay() {
    const element = videoRef.current
    if (!element) return
    if (element.paused) {
      void element.play()
    } else {
      element.pause()
    }
  }

  function handleSeek(value: number | readonly number[]) {
    const target = Array.isArray(value) ? value[0] : (value as number)
    const element = videoRef.current
    if (!element) return
    element.currentTime = target
    setCurrentTime(target)
  }

  return (
    <div className="flex flex-col gap-4">
      {/* value is intentionally `selectedCameraId` (string | null), never
          coerced to `undefined` -- Base UI's Select treats `undefined` as
          "uncontrolled" and `null` as "controlled, nothing selected yet".
          Passing `undefined` here on the first render (before cameras load)
          would flip the component from uncontrolled to controlled the
          moment a camera loads, which Base UI warns about and which broke
          the displayed value actually updating. */}
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

      {error && (
        <div role="alert" className="rounded-md border border-danger bg-danger/10 px-4 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      {video ? (
        <div className="flex flex-col gap-3">
          <div className="relative w-full overflow-hidden rounded-lg border border-border bg-primary">
            <video
              ref={videoRef}
              src={getVideoStreamUrl(video.id)}
              className="block w-full"
              onLoadedMetadata={(event) => {
                const element = event.currentTarget
                setVideoSize({ width: element.videoWidth, height: element.videoHeight })
                setDuration(element.duration)
              }}
              onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />
            <VideoOverlay
              videoRef={videoRef}
              videoWidth={videoSize.width}
              videoHeight={videoSize.height}
              trajectories={trajectories}
              events={events}
              zones={zones}
              lines={lines}
            />
          </div>

          <div className="flex items-center gap-4 rounded-lg border border-border bg-surface p-3">
            <Button type="button" onClick={togglePlay}>
              {isPlaying ? 'Pause' : 'Play'}
            </Button>
            <Slider
              value={[currentTime]}
              min={0}
              max={duration || 1}
              step={0.1}
              onValueChange={handleSeek}
              className="flex-1"
            />
            <span className="w-24 shrink-0 text-right text-sm text-secondary tabular-nums">
              {currentTime.toFixed(1)}s / {duration.toFixed(1)}s
            </span>
          </div>
        </div>
      ) : (
        !error && <p className="text-secondary">No video registered for this camera yet.</p>
      )}
    </div>
  )
}
