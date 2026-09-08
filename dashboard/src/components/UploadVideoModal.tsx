import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { uploadVideo } from '@/lib/api'
import type { Video } from '@/lib/api'
import { UploadCloud, X, AlertTriangle, Loader2 } from 'lucide-react'

interface UploadVideoModalProps {
  isOpen: boolean
  onClose: () => void
  onUploaded: (video: Video, cameraId: string, filename: string) => void
}

type FormState = 'idle' | 'uploading' | 'error'

const ALLOWED_EXTENSIONS = ['.mp4', '.mov']

/**
 * The upload feature's entry point (Cameras page). Deliberately thin: this
 * only owns the POST /videos/upload request itself (file validation +
 * save, seconds at most) -- once that returns a "pending" Video row, the
 * real, potentially minutes-long pipeline run is tracked by
 * RecentUploadsPanel/useVideoStatus polling GET /videos/{id}/status, which
 * survives this modal closing (Step 2's real-progress requirement; nothing
 * here simulates a percentage).
 */
export function UploadVideoModal({ isOpen, onClose, onUploaded }: UploadVideoModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [cameraId, setCameraId] = useState('')
  const [cameraName, setCameraName] = useState('')
  const [state, setState] = useState<FormState>('idle')
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  function reset() {
    setFile(null)
    setCameraId('')
    setCameraName('')
    setState('idle')
    setError(null)
  }

  function handleClose() {
    if (state === 'uploading') return
    reset()
    onClose()
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!file || !cameraId.trim()) return

    const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setError(`Unsupported format ${extension || '(none)'} -- allowed: ${ALLOWED_EXTENSIONS.join(', ')}`)
      setState('error')
      return
    }

    setState('uploading')
    setError(null)
    try {
      const video = await uploadVideo(file, cameraId.trim(), cameraName.trim() || undefined)
      const uploadedFilename = file.name
      const uploadedCameraId = cameraId.trim()
      reset()
      onUploaded(video, uploadedCameraId, uploadedFilename)
      onClose()
    } catch (err: unknown) {
      setError(String(err instanceof Error ? err.message : err))
      setState('error')
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-video-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-primary/70 backdrop-blur-xs p-4"
    >
      <div className="relative flex w-full max-w-md flex-col rounded-xl border border-border bg-surface shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-5 py-4 bg-surface-alt/40">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/15 text-secondary">
              <UploadCloud className="h-4 w-4" />
            </div>
            <div>
              <h2 id="upload-video-title" className="text-base font-semibold text-ink leading-tight">
                Upload Video
              </h2>
              <p className="text-xs text-ink-subtle">Runs through the real detection/tracking pipeline</p>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={handleClose}
            aria-label="Close upload dialog"
            className="text-ink-subtle hover:text-ink"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3.5 p-5">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="upload-file" className="text-xs font-medium text-ink-subtle">
              Video file (.mp4 or .mov, up to 200MB)
            </label>
            <input
              id="upload-file"
              type="file"
              accept=".mp4,.mov,video/mp4,video/quicktime"
              disabled={state === 'uploading'}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="text-xs text-ink-subtle file:mr-2 file:rounded-md file:border-0 file:bg-surface-alt file:px-2.5 file:py-1.5 file:text-xs file:font-medium file:text-ink hover:file:bg-surface-alt/80"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="upload-camera-id" className="text-xs font-medium text-ink-subtle">
              Camera ID
            </label>
            <Input
              id="upload-camera-id"
              value={cameraId}
              onChange={(e) => setCameraId(e.target.value)}
              placeholder="e.g. front-entrance"
              disabled={state === 'uploading'}
              required
            />
            <p className="text-[11px] text-ink-subtle">
              Creates this camera if it doesn't exist yet, or attaches the video to it if it does.
            </p>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="upload-camera-name" className="text-xs font-medium text-ink-subtle">
              Camera name (optional)
            </label>
            <Input
              id="upload-camera-name"
              value={cameraName}
              onChange={(e) => setCameraName(e.target.value)}
              placeholder="e.g. Front Entrance"
              disabled={state === 'uploading'}
            />
          </div>

          <div className="rounded-md border border-border/70 bg-surface-alt/40 p-2.5 text-[11px] text-ink-subtle leading-relaxed">
            This camera has no surveyed calibration, so speed-based events (OVERSPEED, SUDDEN_STOP) are
            suppressed by default for anything uploaded here -- real object detection and tracking still run.
          </div>

          {state === 'error' && error && (
            <div role="alert" className="flex items-start gap-2 rounded-md border border-danger bg-danger/10 px-3 py-2 text-xs text-danger">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <Button type="button" variant="outline" size="sm" onClick={handleClose} disabled={state === 'uploading'}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={!file || !cameraId.trim() || state === 'uploading'} className="gap-1.5">
              {state === 'uploading' ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <UploadCloud className="h-3.5 w-3.5" />
                  Upload
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
