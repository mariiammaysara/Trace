import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { VideoOverlay } from '@/components/VideoOverlay'
import { getVideoStreamUrl } from '@/lib/api'
import type { Line, TraceEvent, Trajectory, Video, Zone } from '@/lib/api'

/**
 * A request to seek the player to a specific time. `nonce` exists so a
 * second click on the same timestamp (same `time`) still re-triggers the
 * effect below -- a plain number prop wouldn't change reference/value in
 * that case.
 */
export interface SeekRequest {
  time: number
  nonce: number
}

interface VideoPlayerProps {
  video: Video
  trajectories: Trajectory[]
  events: TraceEvent[]
  zones: Zone[]
  lines: Line[]
  /** Externally requested seek (e.g. clicking an event row in EventsView). */
  seekRequest?: SeekRequest | null
}

/**
 * Real video playback plus the detection/track/zone/line overlay, synced to
 * <video> via requestAnimationFrame (VideoOverlay). Extracted from LiveView
 * in Phase 10.3 so EventsView's "click an event, jump to that video moment"
 * flow drives this exact same player instead of re-implementing playback --
 * LiveView still owns camera/video selection, this owns the player itself.
 */
export function VideoPlayer({ video, trajectories, events, zones, lines, seekRequest }: VideoPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [videoSize, setVideoSize] = useState({ width: 0, height: 0 })

  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    if (!seekRequest) return
    const element = videoRef.current
    if (element) element.currentTime = seekRequest.time
    setCurrentTime(seekRequest.time)
  }, [seekRequest])

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
        <Slider value={[currentTime]} min={0} max={duration || 1} step={0.1} onValueChange={handleSeek} className="flex-1" />
        <span className="w-24 shrink-0 text-right text-sm text-secondary tabular-nums">
          {currentTime.toFixed(1)}s / {duration.toFixed(1)}s
        </span>
      </div>
    </div>
  )
}
