import { useState, useEffect } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import {
  Video,
  Radio,
  RefreshCw,
  Maximize2,
  Bell,
  Menu,
} from 'lucide-react'
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

export function Header({
  title = 'Dashboard',
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

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      void document.documentElement.requestFullscreen().catch(() => {})
    } else {
      void document.exitFullscreen().catch(() => {})
    }
  }

  const selectedCamera = cameras.find((c) => c.camera_id === selectedCameraId)

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-5 shadow-2xs">
      {/* Left Title & Subtitle */}
      <div className="flex items-center gap-3">
        {onToggleMobileMenu && (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={onToggleMobileMenu}
            className="md:hidden text-primary"
            aria-label="Toggle navigation menu"
          >
            <Menu className="h-4 w-4" />
          </Button>
        )}

        <div className="flex flex-col">
          <div className="flex items-center gap-2">
            <h1 className="text-base font-semibold tracking-tight text-primary leading-tight">
              {title}
            </h1>
            <span className="hidden items-center gap-1 rounded-full border border-success/30 bg-success/10 px-2 py-0.2 text-[10px] font-medium text-success sm:inline-flex">
              <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
              Live Sync
            </span>
          </div>
          <p className="text-[11px] text-secondary hidden sm:block">
            {subtitle}
          </p>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-2.5">
        {/* Camera Selector in Header */}
        <div className="flex items-center gap-1.5">
          <Select
            value={selectedCameraId}
            onValueChange={(value) => onSelectCamera(value)}
          >
            <SelectTrigger
              aria-label="Select active camera feed"
              className="h-8 min-w-[150px] max-w-[200px] border-border bg-background text-xs font-medium text-primary hover:border-secondary transition-colors"
            >
              <div className="flex items-center gap-1.5 truncate">
                <Video className="h-3.5 w-3.5 text-secondary shrink-0" />
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
                    <span className="text-[10px] font-mono text-secondary">
                      #{camera.id}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Live Clock */}
        <div className="hidden lg:flex items-center gap-1.5 rounded-md border border-border bg-surface-alt/40 px-2 py-1 text-[11px] font-mono text-secondary tabular-nums">
          <Radio className="h-3 w-3 text-accent" />
          <span>{timeString}</span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1">
          {onRefresh && (
            <Button
              type="button"
              variant="outline"
              size="icon-sm"
              onClick={onRefresh}
              disabled={isRefreshing}
              aria-label="Refresh live data"
              className="text-secondary hover:text-primary"
            >
              <RefreshCw className={isRefreshing ? 'h-3.5 w-3.5 animate-spin' : 'h-3.5 w-3.5'} />
            </Button>
          )}

          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            onClick={toggleFullscreen}
            aria-label="Toggle fullscreen display"
            className="text-secondary hover:text-primary hidden sm:inline-flex"
          >
            <Maximize2 className="h-3.5 w-3.5" />
          </Button>

          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            aria-label="System notifications"
            className="text-secondary hover:text-primary relative"
          >
            <Bell className="h-3.5 w-3.5" />
            <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-danger" />
          </Button>
        </div>
      </div>
    </header>
  )
}
