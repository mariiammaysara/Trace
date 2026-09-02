import { useState, useEffect } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Video, Radio, RefreshCw, Menu } from 'lucide-react'
import type { Camera } from '@/lib/api'

interface HeaderProps {
  title?: string
  subtitle?: string
  cameras: Camera[]
  selectedCameraId: string | null
  onSelectCamera: (cameraId: string | null) => void
  onToggleMobileMenu?: () => void
  onRefresh?: () => void
  isRefreshing?: boolean
}

/**
 * The app-wide header: page context, the one global camera/source selector,
 * and the one essential action (refresh). Deliberately does not duplicate
 * system status (the sidebar's System Health card already owns that) and
 * dropped fullscreen/notifications -- neither did anything a real operator
 * would reach for (notifications had no real unread state to show).
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

  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-surface px-4 shadow-2xs">
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

      {/* Right: camera/source + essential actions */}
      <div className="flex items-center gap-2.5">
        <Select
          value={selectedCameraId}
          onValueChange={(value) => onSelectCamera(value)}
        >
          <SelectTrigger
            aria-label="Select active camera feed"
            className="h-8 min-w-[150px] max-w-[200px] border-border bg-background text-xs font-medium text-ink hover:border-secondary transition-colors"
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

        <div className="hidden lg:flex items-center gap-1.5 rounded-md border border-border bg-surface-alt/40 px-2 py-1 font-mono text-[11px] text-ink-subtle tabular-nums">
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
