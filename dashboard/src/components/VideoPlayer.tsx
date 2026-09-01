import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { VideoOverlay } from '@/components/VideoOverlay'
import { getVideoStreamUrl } from '@/lib/api'
import type { Line, TraceEvent, Trajectory, Video, Zone } from '@/lib/api'
import {
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  Maximize2,
  Minimize2,
  Layers,
} from 'lucide-react'

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
  seekRequest?: SeekRequest | null
  cameraName?: string | null
}

export function VideoPlayer({
  video,
  trajectories,
  events,
  zones,
  lines,
  seekRequest,
  cameraName,
}: VideoPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [videoSize, setVideoSize] = useState({ width: 0, height: 0 })
  const [isMuted, setIsMuted] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)

  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

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

  function toggleMute() {
    const element = videoRef.current
    if (!element) return
    element.muted = !element.muted
    setIsMuted(element.muted)
  }

  function handleReset() {
    const element = videoRef.current
    if (!element) return
    element.currentTime = 0
    setCurrentTime(0)
  }

  function toggleContainerFullscreen() {
    const container = containerRef.current
    if (!container) return

    if (!document.fullscreenElement) {
      void container.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {})
    } else {
      void document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {})
    }
  }

  return (
    <div ref={containerRef} className="flex flex-col gap-2.5 w-full select-none">
      {/* Video Viewport Container */}
      <div className="group relative w-full overflow-hidden rounded-lg border border-border bg-primary aspect-video max-h-[460px] flex items-center justify-center shadow-xs">
        <video
          ref={videoRef}
          src={getVideoStreamUrl(video.id)}
          muted={isMuted}
          playsInline
          className="block h-full w-full object-contain"
          onLoadedMetadata={(event) => {
            const element = event.currentTarget
            setVideoSize({ width: element.videoWidth, height: element.videoHeight })
            setDuration(element.duration)
          }}
          onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
        />

        {/* HUD Overlay: Top Left Telemetry */}
        <div className="pointer-events-none absolute top-3 left-3 flex items-center gap-2 z-10">
          <div className="flex items-center gap-1.5 rounded bg-primary/80 backdrop-blur-xs px-2 py-1 text-[11px] font-mono text-surface border border-white/10 shadow-xs">
            <span className="relative flex h-2 w-2">
              <span className={isPlaying ? 'absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75' : 'hidden'} />
              <span className={`relative inline-flex h-2 w-2 rounded-full ${isPlaying ? 'bg-success' : 'bg-warning'}`} />
            </span>
            <span className="font-semibold">{isPlaying ? 'LIVE' : 'PAUSED'}</span>
          </div>

          {cameraName && (
            <div className="rounded bg-primary/80 backdrop-blur-xs px-2 py-1 text-[11px] font-mono text-surface/90 border border-white/10 shadow-xs">
              CAM: {cameraName}
            </div>
          )}
        </div>

        {/* HUD Overlay: Top Right Telemetry */}
        <div className="pointer-events-none absolute top-3 right-3 flex items-center gap-2 z-10">
          <div className="flex items-center gap-1.5 rounded bg-primary/80 backdrop-blur-xs px-2 py-1 text-[11px] font-mono text-surface/90 border border-white/10 shadow-xs">
            <Layers className="h-3 w-3 text-accent" />
            <span>{trajectories.length} Tracks</span>
          </div>
          {videoSize.width > 0 && (
            <div className="hidden sm:flex items-center rounded bg-primary/80 backdrop-blur-xs px-2 py-1 text-[11px] font-mono text-surface/70 border border-white/10 shadow-xs">
              {videoSize.width}×{videoSize.height}
            </div>
          )}
        </div>

        {/* Synchronized Vector Overlay */}
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

      {/* Control Bar */}
      <div className="flex items-center gap-3 rounded-lg border border-border bg-surface px-3.5 py-2 shadow-2xs">
        <Button
          type="button"
          onClick={togglePlay}
          size="sm"
          className="gap-1.5 text-xs font-semibold px-3"
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
          <span>{isPlaying ? 'Pause' : 'Play'}</span>
        </Button>

        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          onClick={handleReset}
          aria-label="Rewind to start"
          className="text-secondary hover:text-primary"
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          onClick={toggleMute}
          aria-label={isMuted ? 'Unmute' : 'Mute'}
          className="text-secondary hover:text-primary"
        >
          {isMuted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
        </Button>

        {/* Scrubber Slider */}
        <Slider
          value={[currentTime]}
          min={0}
          max={duration || 1}
          step={0.1}
          onValueChange={handleSeek}
          className="flex-1"
          aria-label="Video playback progress"
        />

        {/* Timestamp */}
        <span className="w-24 shrink-0 text-right text-xs font-mono text-secondary tabular-nums font-medium">
          {currentTime.toFixed(1)}s / {duration.toFixed(1)}s
        </span>

        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          onClick={toggleContainerFullscreen}
          aria-label="Fullscreen player"
          className="text-secondary hover:text-primary"
        >
          {isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
        </Button>
      </div>
    </div>
  )
}
