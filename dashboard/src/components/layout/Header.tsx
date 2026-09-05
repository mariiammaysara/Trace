import { useState, useEffect } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Video, Radio, RefreshCw, Menu, Sparkles, Crosshair, AlertTriangle } from 'lucide-react'
import type { Camera } from '@/lib/api'
import { cn } from '@/lib/utils'

interface HeaderProps {
  title?: string
  subtitle?: string
  cameras: Camera[]
  selectedCameraId: string | null
  onSelectCamera: (cameraId: string | null) => void
  onToggleMobileMenu?: () => void
  onRefresh?: () => void
  isRefreshing?: boolean
  /** Phase 20: Launches the pre-recorded demo scenarios modal */
  onOpenDemoModal?: () => void
  /** Mirrors the last listCameras() call's success/failure -- the same real
   * signal the Sidebar's System Health card already uses, surfaced here too
   * as the Operations Telemetry Strip's health pulse. */
  isApiConnected?: boolean
  /** Optional -- lets the "N FEEDS CONNECTED" badge double as a shortcut to
   * the Cameras page. Renders as a plain (non-interactive) badge without it. */
  onNavigateToCameras?: () => void
  /** Real, already-fetched count for the selected camera (trajectories.length)
   * -- omit (undefined) rather than show a 0 when no camera/scene is loaded
   * yet, so this never implies a reading that doesn't exist. */
  targetsInFrame?: number
  /** Count of currently-real danger-severity events for the selected camera
   * (reusing eventSeverity.ts's own classification). 0 or omitted hides the
   * chip entirely -- it is never shown "empty." */
  criticalEventCount?: number
  /** Jumps to the most recent critical event's timestamp on the Live page.
   * Only rendered when both this and a positive criticalEventCount are set. */
  onSeekToCriticalEvent?: () => void
}

/**
 * The app-wide header: page context, an Operations Telemetry Strip (system
 * health, sensor count, live target count, critical-breach shortcut), the
 * one global camera/source selector, and the one essential action
 * (refresh). Every telemetry figure here is real, already-fetched data --
 * see each prop's own comment for where it comes from; none of it is
 * estimated or invented (there is deliberately no FPS/latency reading here:
 * the backend doesn't compute one anywhere the frontend can read it yet).
 */
export function Header({
  title = 'Overview',
  subtitle = 'Real-time overview of your video intelligence system',
  cameras,
  selectedCameraId,
  onSelectCamera,
  onToggleMobileMenu,
  onRefresh,
  isRefreshing = false,
  onOpenDemoModal,
  isApiConnected = true,
  onNavigateToCameras,
  targetsInFrame,
  criticalEventCount = 0,
  onSeekToCriticalEvent,
}: HeaderProps) {
  const [timeString, setTimeString] = useState<string>('')

  useEffect(() => {
    const update = () => {
      const now = new Date()
      setTimeString(
        now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' UTC',
      )
    }
    update()
    const timer = setInterval(update, 1000)
    return () => clearInterval(timer)
  }, [])

  const selectedCamera = cameras.find((c) => c.camera_id === selectedCameraId)
  const showCriticalChip = criticalEventCount > 0 && !!onSeekToCriticalEvent

  return (
    <header className="flex min-h-12 shrink-0 flex-wrap items-center justify-between gap-y-2 border-b border-border bg-surface px-4 py-2 shadow-2xs">
      {/* Left: page context */}
      <div className="flex items-center gap-3">
        {onToggleMobileMenu && (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={onToggleMobileMenu}
            className="md:hidden text-ink"
            aria-label="Toggle navigation menu"
          >
            <Menu className="h-4 w-4" />
          </Button>
        )}

        <div className="flex flex-col">
          <h1 className="text-base font-semibold tracking-tight text-ink leading-tight">
            {title}
          </h1>
          <p className="text-[11px] text-ink-quiet hidden sm:block">
            {subtitle}
          </p>
        </div>
      </div>

      {/* Center: Operations Telemetry Strip -- real system/scene status, not
          decorative. Hidden progressively on narrower viewports, critical
          breach chip excepted (that one always shows: it demands attention
          regardless of screen size). */}
      <div className="flex items-center gap-2 order-3 basis-full lg:order-none lg:basis-auto">
        <div
          className={cn(
            'hidden md:flex items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-[10px] font-semibold tracking-wide',
            isApiConnected ? 'border-success/30 bg-success/10 text-success' : 'border-danger/30 bg-danger/10 text-danger',
          )}
        >
          <span className="relative flex h-1.5 w-1.5">
            {isApiConnected && (
              <span className="motion-safe:absolute motion-safe:inline-flex h-full w-full motion-safe:animate-ping rounded-full bg-success opacity-75" />
            )}
            <span className={cn('relative inline-flex h-1.5 w-1.5 rounded-full', isApiConnected ? 'bg-success' : 'bg-danger')} />
          </span>
          <span>{isApiConnected ? 'SYSTEM ONLINE' : 'SYSTEM OFFLINE'}</span>
        </div>

        <div
          role={onNavigateToCameras ? 'button' : undefined}
          tabIndex={onNavigateToCameras ? 0 : undefined}
          onClick={onNavigateToCameras}
          onKeyDown={
            onNavigateToCameras
              ? (event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    onNavigateToCameras()
                  }
                }
              : undefined
          }
          className={cn(
            'hidden lg:flex items-center gap-1.5 rounded-md border border-border bg-surface-alt/40 px-2 py-1 font-mono text-[10px] font-semibold text-ink-quiet',
            onNavigateToCameras && 'cursor-pointer hover:border-accent/40 hover:text-ink transition-colors',
          )}
        >
          <Video className="h-3 w-3 text-ink-subtle" />
          <span>{cameras.length} FEED{cameras.length === 1 ? '' : 'S'} CONNECTED</span>
        </div>

        {typeof targetsInFrame === 'number' && (
          <div className="hidden xl:flex items-center gap-1.5 rounded-md border border-border bg-surface-alt/40 px-2 py-1 font-mono text-[10px] font-semibold text-ink-quiet">
            <Crosshair className="h-3 w-3 text-accent" />
            <span>{targetsInFrame} TARGET{targetsInFrame === 1 ? '' : 'S'} IN FRAME</span>
          </div>
        )}

        {showCriticalChip && (
          <button
            type="button"
            onClick={onSeekToCriticalEvent}
            aria-label={`${criticalEventCount} critical breach${criticalEventCount === 1 ? '' : 'es'} -- jump to the most recent one`}
            className="flex items-center gap-1.5 rounded-md border border-danger/50 bg-danger/15 px-2 py-1 font-mono text-[10px] font-bold text-danger motion-safe:animate-pulse hover:bg-danger/25 transition-colors"
          >
            <AlertTriangle className="h-3 w-3" />
            <span>{criticalEventCount} CRITICAL BREACH{criticalEventCount === 1 ? '' : 'ES'}</span>
          </button>
        )}
      </div>

      {/* Right: camera/source + demo scenarios + essential actions */}
      <div className="flex items-center gap-2.5">
        {onOpenDemoModal && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onOpenDemoModal}
            className="h-8 gap-1.5 border-accent/40 bg-accent/5 backdrop-blur-sm text-ink hover:bg-accent/15 text-xs font-semibold shadow-2xs"
          >
            <Sparkles className="h-3.5 w-3.5 text-secondary" />
            <span className="hidden sm:inline">Demo Scenarios</span>
          </Button>
        )}

        <Select
          value={selectedCameraId}
          onValueChange={(value) => onSelectCamera(value)}
        >
          <SelectTrigger
            aria-label="Select active camera feed"
            className="h-8 min-w-[150px] max-w-[200px] border-border bg-surface-alt/60 backdrop-blur-sm text-xs font-medium text-ink hover:border-secondary transition-colors"
          >
            <div className="flex items-center gap-1.5 truncate">
              <Video className="h-3.5 w-3.5 text-ink-subtle shrink-0" />
              <SelectValue placeholder="Select camera">
                {selectedCamera?.name ?? selectedCameraId ?? 'Select camera'}
              </SelectValue>
            </div>
          </SelectTrigger>
          <SelectContent>
            {cameras.map((camera) => (
              <SelectItem key={camera.camera_id} value={camera.camera_id}>
                <div className="flex items-center justify-between w-full gap-3">
                  <span>{camera.name ?? camera.camera_id}</span>
                  <span className="font-mono text-[10px] text-ink-subtle">
                    #{camera.id}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="hidden lg:flex items-center gap-1.5 rounded-md border border-border bg-surface-alt/60 backdrop-blur-sm px-2 py-1 font-mono text-[11px] text-ink-subtle tabular-nums">
          <Radio className="h-3 w-3 text-accent" />
          <span>{timeString}</span>
        </div>

        {onRefresh && (
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            onClick={onRefresh}
            disabled={isRefreshing}
            aria-label="Refresh live data"
            className="text-ink-subtle hover:text-ink"
          >
            <RefreshCw className={isRefreshing ? 'h-3.5 w-3.5 animate-spin' : 'h-3.5 w-3.5'} />
          </Button>
        )}
      </div>
    </header>
  )
}
