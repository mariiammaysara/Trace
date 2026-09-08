import { useState, useEffect } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { RefreshCw, Menu, Film, ChevronDown } from 'lucide-react'
import type { Camera } from '@/lib/api'
import { cn } from '@/lib/utils'

interface HeaderProps {
  title?: string
  cameras: Camera[]
  selectedCameraId: string | null
  onSelectCamera: (cameraId: string | null) => void
  onToggleMobileMenu?: () => void
  onRefresh?: () => void
  isRefreshing?: boolean
  /** Phase 20: Launches the pre-recorded demo scenarios modal */
  onOpenDemoModal?: () => void
  /** Mirrors the last listCameras() call's success/failure -- the same real
   * signal the Sidebar's System Health card already uses. */
  isApiConnected?: boolean
  /** Real, already-fetched count for the selected camera (trajectories.length)
   * -- omit (undefined) rather than show a 0 when no camera/scene is loaded
   * yet, so this never implies a reading that doesn't exist. */
  targetsInFrame?: number
  /** Count of currently-real danger-severity events for the selected camera
   * (reusing eventSeverity.ts's own classification). 0 or omitted hides the
   * segment entirely -- it is never shown "empty." */
  criticalEventCount?: number
  /** Jumps to the most recent critical event's timestamp on the Live page.
   * Only rendered when both this and a positive criticalEventCount are set. */
  onSeekToCriticalEvent?: () => void
}

/**
 * The app-wide top bar: a single razor-thin (h-12) utility strip, not a
 * stack of badges. Every telemetry figure here is real, already-fetched
 * data -- see each prop's own comment for where it comes from; none of it
 * is estimated or invented (there is deliberately no FPS/latency reading:
 * the backend doesn't compute one anywhere the frontend can read it yet).
 * No decorative glow, no ping/pulse animation -- system state is a plain
 * 6px dot, critical breach is plain rose text, nothing radiates.
 */
export function Header({
  title = 'Overview',
  cameras,
  selectedCameraId,
  onSelectCamera,
  onToggleMobileMenu,
  onRefresh,
  isRefreshing = false,
  onOpenDemoModal,
  isApiConnected = true,
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
  const showCriticalSegment = criticalEventCount > 0 && !!onSeekToCriticalEvent

  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-primary/90 backdrop-blur-md px-4">
      {/* Left: page title + minimal camera selector */}
      <div className="flex items-center gap-3 shrink-0">
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

        <h1 className="text-lg font-semibold tracking-tight text-ink">{title}</h1>

        <span className="hidden sm:block h-4 w-px bg-border" aria-hidden="true" />

        <Select value={selectedCameraId} onValueChange={(value) => onSelectCamera(value)}>
          <SelectTrigger
            aria-label="Select active camera feed"
            className="hidden sm:flex h-7 gap-1 border-none bg-transparent px-1.5 font-mono text-xs text-ink-secondary shadow-none hover:bg-white/[0.04] hover:text-ink"
          >
            <SelectValue placeholder="Select camera">
              {selectedCamera?.name ?? selectedCameraId ?? 'Select camera'}
            </SelectValue>
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
      </div>

      {/* Center: quiet, pipe-separated inline telemetry -- text, not badges. */}
      <div className="flex flex-1 min-w-0 items-center justify-center gap-1.5 overflow-hidden whitespace-nowrap font-mono text-[11px]">
        <span className="hidden md:inline text-ink-subtle">System:</span>
        <span className={cn('hidden md:flex items-center gap-1.5', isApiConnected ? 'text-success' : 'text-danger')}>
          <span className={cn('h-1.5 w-1.5 rounded-full', isApiConnected ? 'bg-success' : 'bg-danger')} />
          {isApiConnected ? 'Operational' : 'Offline'}
        </span>

        <span className="hidden md:inline text-border">|</span>
        <span className="hidden md:inline text-ink-subtle">Feeds:</span>
        <span className="hidden md:inline text-ink">{cameras.length}</span>

        {typeof targetsInFrame === 'number' && (
          <>
            <span className="hidden lg:inline text-border">|</span>
            <span className="hidden lg:inline text-ink-subtle">Targets:</span>
            <span className="hidden lg:inline text-ink">{targetsInFrame}</span>
          </>
        )}

        {showCriticalSegment && (
          <>
            <span className="text-border">|</span>
            <button
              type="button"
              onClick={onSeekToCriticalEvent}
              className="font-semibold text-danger hover:underline"
            >
              {criticalEventCount} Breach{criticalEventCount === 1 ? '' : 'es'}
            </button>
          </>
        )}
      </div>

      {/* Right: clock + demo scenarios + refresh */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="hidden lg:inline font-mono text-[11px] text-ink-subtle tabular-nums">
          {timeString}
        </span>

        {onOpenDemoModal && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onOpenDemoModal}
            className="gap-2 rounded-md border border-white/10 bg-primary/80 px-3 font-mono text-xs text-ink-secondary hover:border-white/20 hover:bg-primary hover:text-ink transition-colors"
          >
            <Film className="h-3.5 w-3.5 text-ink-subtle" />
            <span className="hidden sm:inline">Scenarios</span>
            <ChevronDown className="h-3 w-3 opacity-60" />
          </Button>
        )}

        {onRefresh && (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={onRefresh}
            disabled={isRefreshing}
            aria-label="Refresh live data"
            className="text-ink-subtle hover:bg-white/[0.04] hover:text-ink"
          >
            <RefreshCw className={isRefreshing ? 'h-3.5 w-3.5 animate-spin' : 'h-3.5 w-3.5'} />
          </Button>
        )}
      </div>
    </header>
  )
}
