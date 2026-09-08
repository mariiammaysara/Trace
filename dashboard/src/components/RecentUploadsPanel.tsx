import { Button } from '@/components/ui/button'
import { useVideoStatus } from '@/hooks/useVideoStatus'
import { cn } from '@/lib/utils'
import { CheckCircle2, XCircle, Loader2, Clock, PlayCircle } from 'lucide-react'

export interface UploadEntry {
  videoId: number
  cameraId: string
  filename: string
  createdAt: number
}

interface RecentUploadsPanelProps {
  uploads: UploadEntry[]
  onViewLive: (cameraId: string) => void
}

function formatEta(seconds: number): string {
  if (seconds < 60) return `${Math.ceil(seconds)}s`
  const minutes = Math.floor(seconds / 60)
  const remainder = Math.round(seconds % 60)
  return `${minutes}m ${remainder}s`
}

function UploadRow({ upload, onViewLive }: { upload: UploadEntry; onViewLive: (cameraId: string) => void }) {
  const { status, error } = useVideoStatus(upload.videoId)

  const state = status?.status ?? 'pending'

  return (
    <div className="flex flex-col gap-1.5 px-3.5 py-2.5">
      <div className="flex items-center gap-2.5">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-surface-alt text-ink-subtle">
          {state === 'done' && <CheckCircle2 className="h-3.5 w-3.5 text-success" />}
          {state === 'failed' && <XCircle className="h-3.5 w-3.5 text-danger" />}
          {(state === 'pending' || state === 'processing') && (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-secondary" />
          )}
        </div>
        <div className="flex flex-1 flex-col min-w-0">
          <span className="text-sm font-medium text-ink truncate">{upload.filename}</span>
          <span className="text-[11px] font-mono text-ink-subtle truncate">{upload.cameraId}</span>
        </div>
        <span
          className={cn(
            'shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
            state === 'done' && 'border-success/30 bg-success/10 text-success',
            state === 'failed' && 'border-danger/30 bg-danger/10 text-danger',
            (state === 'pending' || state === 'processing') && 'border-secondary/30 bg-secondary/10 text-secondary',
          )}
        >
          {state}
        </span>
        {state === 'done' && (
          <Button type="button" size="xs" variant="outline" className="gap-1 text-[11px]" onClick={() => onViewLive(upload.cameraId)}>
            <PlayCircle className="h-3 w-3" />
            View Live
          </Button>
        )}
      </div>

      {state === 'processing' && status && status.total_frames && (
        <div className="flex flex-col gap-1 pl-[2.375rem]">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-alt">
            <div
              className="h-full rounded-full bg-secondary transition-[width]"
              style={{ width: `${status.percent ?? 0}%` }}
            />
          </div>
          <div className="flex items-center gap-2.5 text-[11px] text-ink-subtle">
            <span>
              {status.frames_processed} / {status.total_frames} frames
            </span>
            {status.current_fps !== null && <span>{status.current_fps.toFixed(1)} FPS</span>}
            {status.eta_seconds !== null && (
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                ~{formatEta(status.eta_seconds)} left
              </span>
            )}
          </div>
        </div>
      )}

      {state === 'failed' && status?.error_message && (
        <p className="pl-[2.375rem] text-[11px] text-danger">{status.error_message}</p>
      )}

      {error && <p className="pl-[2.375rem] text-[11px] text-danger">Couldn't reach status endpoint: {error}</p>}
    </div>
  )
}

/**
 * A simple home base for uploads (Step 4) -- entries are held by the parent
 * (lifted to App.tsx, not local to this page) so navigating away mid-
 * processing and coming back doesn't lose track of it. Each row polls its
 * own real status independently via useVideoStatus.
 */
export function RecentUploadsPanel({ uploads, onViewLive }: RecentUploadsPanelProps) {
  if (uploads.length === 0) return null

  const sorted = [...uploads].sort((a, b) => b.createdAt - a.createdAt)

  return (
    <div className="flex flex-col gap-2">
      <span className="px-3.5 text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">
        Recent Uploads
      </span>
      <div className="rounded-lg border border-border bg-surface divide-y divide-border overflow-hidden">
        {sorted.map((upload) => (
          <UploadRow key={upload.videoId} upload={upload} onViewLive={onViewLive} />
        ))}
      </div>
    </div>
  )
}
