import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Video, CheckCircle2, Radio } from 'lucide-react'
import type { Camera } from '@/lib/api'
import { cn } from '@/lib/utils'

interface CameraFleetCardProps {
  cameras: Camera[]
  activeCameraId: string | null
  onSelectCamera: (cameraId: string) => void
  className?: string
}

export function CameraFleetCard({
  cameras,
  activeCameraId,
  onSelectCamera,
  className,
}: CameraFleetCardProps) {
  return (
    <Card className={cn('flex flex-col border-border bg-surface shadow-2xs', className)}>
      <CardHeader className="flex flex-row items-center justify-between border-b border-border/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <CardTitle className="text-sm font-semibold tracking-tight text-primary flex items-center gap-1.5">
            <Video className="h-4 w-4 text-secondary" />
            Active Fleet
          </CardTitle>
          <span className="rounded-full bg-surface-alt px-1.5 py-0.2 text-[10px] font-mono font-medium text-secondary">
            {cameras.length} feeds
          </span>
        </div>
      </CardHeader>

      <CardContent className="p-0 divide-y divide-border/30 overflow-y-auto max-h-[220px]">
        {cameras.length === 0 ? (
          <p className="p-4 text-xs text-secondary text-center">No cameras connected.</p>
        ) : (
          cameras.map((camera) => {
            const isActive = camera.camera_id === activeCameraId

            return (
              <div
                key={camera.camera_id}
                className={cn(
                  'flex items-center justify-between px-3.5 py-2.5 transition-colors',
                  isActive ? 'bg-surface-alt/60' : 'hover:bg-surface-alt/30',
                )}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="relative flex h-7 w-7 items-center justify-center rounded-md bg-surface-alt text-primary shrink-0">
                    <Video className="h-3.5 w-3.5 text-secondary" />
                    {isActive && (
                      <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                        <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
                      </span>
                    )}
                  </div>

                  <div className="flex flex-col min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-semibold text-primary truncate">
                        {camera.name ?? camera.camera_id}
                      </span>
                      {isActive && (
                        <span className="rounded bg-secondary/15 px-1 py-0.2 text-[9px] font-mono font-medium text-secondary">
                          ACTIVE
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-secondary font-mono truncate">
                      ID: {camera.camera_id} {camera.location ? `• ${camera.location}` : ''}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    type="button"
                    variant={isActive ? 'secondary' : 'outline'}
                    size="xs"
                    onClick={() => onSelectCamera(camera.camera_id)}
                    className="text-[11px]"
                  >
                    {isActive ? (
                      <span className="flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3 text-success" /> Live
                      </span>
                    ) : (
                      'Switch'
                    )}
                  </Button>
                </div>
              </div>
            )
          })
        )}
      </CardContent>
    </Card>
  )
}
