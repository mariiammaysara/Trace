import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { VideoOverlay } from '@/components/VideoOverlay'
import { LiveIncidentBanner } from '@/components/LiveIncidentBanner'
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
  VideoOff,
  Rewind,
  FastForward,
} from 'lucide-react'

/** Investigation's "scrub ±5s around the event" control (Phase 18) --
 * reused here, not duplicated, since every page (Overview, Live, Events,
 * Investigation) shares this one VideoPlayer. */
const SCRUB_SECONDS = 5

/** Mirrors HTMLMediaElement.error.code -- see MDN MediaError. */
const MEDIA_ERROR_MESSAGES: Record<number, string> = {
  1: 'Playback was aborted.',
  2: 'A network error interrupted the video stream.',
  3: 'The video stream is corrupted or could not be decoded.',
  4: "The video codec isn't supported by this browser.",
}

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
  /** Phase 19: passed straight through to VideoOverlay -- clicking a
   * tracked object's box opens its Object Profile. */
  onSelectObject?: (objectId: number) => void
  /** Phase 20: surfaces real-time event alerts during demo/playback. */
  onInvestigateEvent?: (eventId: number) => void
  activeScenarioTitle?: string | null
}

export function VideoPlayer({
  video,
  trajectories,
  events,
  zones,
  lines,
  seekRequest,
  cameraName,
  onSelectObject,
  onInvestigateEvent,
  activeScenarioTitle,
}: VideoPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [videoSize, setVideoSize] = useState({ width: 0, height: 0 })
  const [isMuted, setIsMuted] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [mediaError, setMediaError] = useState<string | null>(null)

  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Reset error state whenever the underlying video record changes so a
  // camera switch gets a fresh chance to load, not a stale error banner.
  // Some backend stream failures never fire a `error` event at all -- the
  // connection just stays in NETWORK_LOADING/HAVE_NOTHING forever (observed
  // against the real Phase 9/10 API) -- so this also arms a load timeout:
  // if metadata hasn't arrived in a reasonable window, treat it as failed
  // rather than showing a blank box indefinitely.
  useEffect(() => {
    setMediaError(null)
    const timeout = window.setTimeout(() => {
      setMediaError((current) => current ?? (videoRef.current?.readyState ? null : 'The video stream is taking too long to respond.'))
    }, 10_000)
    return () => window.clearTimeout(timeout)
  }, [video.id])

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

  function nudge(deltaSeconds: number) {
    const element = videoRef.current
    if (!element) return
    const ceiling = duration || element.duration || Infinity
    const target = Math.min(Math.max(element.currentTime + deltaSeconds, 0), ceiling)
    element.currentTime = target
    setCurrentTime(target)
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
      {/* Video Viewport Container -- a compact fixed-height box while the
          stream is unavailable, so a failure doesn't claim the same visual
          weight as a working feed; full aspect-video once there's something
          to actually show. */}
      <div
        className={
          mediaError
            ? 'group relative w-full overflow-hidden rounded-lg border border-border bg-primary h-[200px] flex items-center justify-center shadow-xs'
            : 'group relative w-full overflow-hidden rounded-lg border border-border bg-primary aspect-video max-h-[460px] flex items-center justify-center shadow-xs'
        }
      >
        <video
          ref={videoRef}
          src={getVideoStreamUrl(video.id)}
          muted={isMuted}
          playsInline
          className={mediaError ? 'hidden' : 'block h-full w-full object-contain'}
          onLoadedMetadata={(event) => {
            const element = event.currentTarget
            setVideoSize({ width: element.videoWidth, height: element.videoHeight })
            setDuration(element.duration)
          }}
          onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onError={(event) => {
            const code = event.currentTarget.error?.code
            setMediaError((code !== undefined && MEDIA_ERROR_MESSAGES[code]) || 'This video could not be played.')
          }}
        />

        {mediaError && (
          <div className="flex flex-col items-center gap-1.5 px-6 text-center">
            <VideoOff className="h-4 w-4 text-warning" />
            <p className="text-xs font-semibold text-ink-on-dark">Video unavailable</p>
            <p className="max-w-xs text-[11px] text-ink-on-dark-subtle">{mediaError}</p>
            <Button
              type="button"
              variant="outline"
              size="xs"
              onClick={() => {
                setMediaError(null)
                videoRef.current?.load()
              }}
              className="mt-1 border-white/20 bg-transparent text-ink-on-dark-quiet hover:bg-white/10 hover:text-ink-on-dark"
            >
              Retry
            </Button>
          </div>
        )}

        {!mediaError && (
          <>
            {/* HUD Overlay: Top Left Telemetry */}
            <div className="pointer-events-none absolute top-3 left-3 flex items-center gap-2 z-10">
              <div className="flex items-center gap-1.5 rounded bg-primary/80 backdrop-blur-xs px-2 py-1 font-mono text-[11px] text-ink-on-dark border border-white/10 shadow-xs">
                <span className="relative flex h-2 w-2">
                  <span className={isPlaying ? 'motion-safe:absolute motion-safe:inline-flex h-full w-full motion-safe:animate-ping rounded-full bg-success opacity-75' : 'hidden'} />
                  <span className={`relative inline-flex h-2 w-2 rounded-full ${isPlaying ? 'bg-success' : 'bg-warning'}`} />
                </span>
                <span className="font-semibold">{isPlaying ? 'LIVE' : 'PAUSED'}</span>
              </div>

              {cameraName && (
                <div className="rounded bg-primary/80 backdrop-blur-xs px-2 py-1 font-mono text-[11px] text-ink-on-dark-quiet border border-white/10 shadow-xs">
                  CAM: {cameraName}
                </div>
              )}
            </div>

            {/* HUD Overlay: Top Right Telemetry */}
            <div className="pointer-events-none absolute top-3 right-3 flex items-center gap-2 z-10">
              <div className="flex items-center gap-1.5 rounded bg-primary/80 backdrop-blur-xs px-2 py-1 font-mono text-[11px] text-ink-on-dark-quiet border border-white/10 shadow-xs">
                <Layers className="h-3 w-3 text-accent" />
                <span>{trajectories.length} Tracks</span>
              </div>
            </div>
          </>
        )}

        {/* Synchronized Vector Overlay */}
        {!mediaError && (
          <>
            <VideoOverlay
              videoRef={videoRef}
              videoWidth={videoSize.width}
              videoHeight={videoSize.height}
              trajectories={trajectories}
              events={events}
              zones={zones}
              lines={lines}
              onSelectObject={onSelectObject}
            />

            {onInvestigateEvent && (
              <LiveIncidentBanner
                currentTime={currentTime}
                events={events}
                onInvestigateEvent={onInvestigateEvent}
                activeScenarioTitle={activeScenarioTitle}
              />
            )}
          </>
        )}
      </div>

      {/* Control Bar */}
      <div className="flex items-center gap-3 rounded-lg border border-border bg-surface px-3.5 py-2 shadow-2xs">
        <Button
          type="button"
          onClick={togglePlay}
          size="sm"
          disabled={!!mediaError}
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
          disabled={!!mediaError}
          aria-label="Rewind to start"
          className="text-ink-subtle hover:text-ink"
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="outline"
          size="icon-sm"
          onClick={toggleMute}
          disabled={!!mediaError}
          aria-label={isMuted ? 'Unmute' : 'Mute'}
          className="text-ink-subtle hover:text-ink"
        >
          {isMuted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
        </Button>

        {/* Scrub ±5s -- lets investigating an incident jump to and frame the
            exact moment, without hunting on the slider for a precise offset. */}
        <div className="flex items-center gap-0.5 border-l border-border pl-3 -ml-0.5">
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            onClick={() => nudge(-SCRUB_SECONDS)}
            disabled={!!mediaError}
            aria-label={`Back ${SCRUB_SECONDS} seconds`}
            title={`Back ${SCRUB_SECONDS}s`}
            className="text-ink-subtle hover:text-ink"
          >
            <Rewind className="h-3.5 w-3.5" />
          </Button>
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            onClick={() => nudge(SCRUB_SECONDS)}
            disabled={!!mediaError}
            aria-label={`Forward ${SCRUB_SECONDS} seconds`}
            title={`Forward ${SCRUB_SECONDS}s`}
            className="text-ink-subtle hover:text-ink"
          >
            <FastForward className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* Scrubber Slider */}
        <Slider
          value={[currentTime]}
          min={0}
          max={duration || 1}
          step={0.1}
          onValueChange={handleSeek}
          disabled={!!mediaError}
          className="flex-1"
          aria-label="Video playback progress"
        />

        {/* Timestamp */}
        <span className="w-24 shrink-0 text-right font-mono text-xs text-ink-subtle tabular-nums font-medium">
          {currentTime.toFixed(1)}s / {duration.toFixed(1)}s
        </span>

        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          onClick={toggleContainerFullscreen}
          aria-label="Fullscreen player"
          className="text-ink-subtle hover:text-ink"
        >
          {isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
        </Button>
      </div>
    </div>
  )
}
