import { useState, type DragEvent, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { uploadVideo } from '@/lib/api'
import type { Video } from '@/lib/api'
import { UploadCloud, FileVideo, X, AlertTriangle, Loader2 } from 'lucide-react'

interface UploadVideoModalProps {
  isOpen: boolean
  onClose: () => void
  onUploaded: (video: Video, cameraId: string, filename: string) => void
}

type FormState = 'idle' | 'uploading' | 'error'

const ALLOWED_EXTENSIONS = ['.mp4', '.mov']

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Dense, high-contrast text-field look shared by both inputs -- overrides
// the shared <Input>'s default shadcn sizing/border via className (cn's
// tailwind-merge dedups the conflicting utilities), same override pattern
// already used elsewhere in this codebase (e.g. DemoScenariosModal's own
// Button color overrides) rather than a second input primitive.
const FIELD_CLASSES =
  'bg-surface-alt/80 border-border focus-visible:border-accent/50 focus-visible:ring-accent/20 rounded-md px-3 py-2 h-auto text-xs font-mono text-ink placeholder:text-ink-disabled'

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
  const [isDragging, setIsDragging] = useState(false)

  if (!isOpen) return null

  function reset() {
    setFile(null)
    setCameraId('')
    setCameraName('')
    setState('idle')
    setError(null)
    setIsDragging(false)
  }

  function handleClose() {
    if (state === 'uploading') return
    reset()
    onClose()
  }

  function handleDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault()
    setIsDragging(false)
    if (state === 'uploading') return
    const dropped = e.dataTransfer.files?.[0] ?? null
    if (dropped) setFile(dropped)
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-primary/70 backdrop-blur-md p-4"
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
              <p className="text-xs font-mono text-ink-subtle">Runs through the real detection/tracking pipeline</p>
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
            <label
              htmlFor="upload-file"
              className="text-[11px] font-mono text-ink-subtle uppercase tracking-wider mb-1.5"
            >
              Video File
            </label>
            <label
              htmlFor="upload-file"
              onDragEnter={(e) => {
                e.preventDefault()
                setIsDragging(true)
              }}
              onDragOver={(e) => e.preventDefault()}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`flex flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed p-4 text-center transition-colors ${
                state === 'uploading' ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'
              } ${isDragging ? 'border-accent/50 bg-accent/5' : 'border-border hover:border-accent/50 bg-surface-alt/40'}`}
            >
              <input
                id="upload-file"
                type="file"
                accept=".mp4,.mov,video/mp4,video/quicktime"
                disabled={state === 'uploading'}
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="sr-only"
              />
              {file ? (
                <div className="flex w-full items-center gap-2 rounded-md border border-border bg-surface px-2.5 py-1.5">
                  <FileVideo className="h-3.5 w-3.5 shrink-0 text-ink-subtle" />
                  <span className="flex-1 min-w-0 truncate text-left text-xs font-mono text-ink">{file.name}</span>
                  <span className="shrink-0 rounded border border-accent/40 bg-accent/10 px-2 py-0.5 text-[10px] font-mono text-accent">
                    {formatFileSize(file.size)}
                  </span>
                </div>
              ) : (
                <>
                  <UploadCloud className="h-5 w-5 text-ink-subtle" />
                  <span className="text-xs font-mono text-ink-subtle">
                    Drag & drop a video, or click to browse
                  </span>
                  <span className="text-[10px] font-mono text-ink-disabled">.mp4 / .mov, up to 200MB</span>
                </>
              )}
            </label>
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="upload-camera-id"
              className="text-[11px] font-mono text-ink-subtle uppercase tracking-wider mb-1.5"
            >
              Camera ID
            </label>
            <Input
              id="upload-camera-id"
              value={cameraId}
              onChange={(e) => setCameraId(e.target.value)}
              placeholder="e.g. front-entrance"
              disabled={state === 'uploading'}
              required
              className={FIELD_CLASSES}
            />
            <p className="text-[11px] text-ink-subtle">Creates the camera if it doesn't already exist.</p>
          </div>

          <div className="flex flex-col gap-1.5">
            <label
              htmlFor="upload-camera-name"
              className="text-[11px] font-mono text-ink-subtle uppercase tracking-wider mb-1.5"
            >
              Camera Name (optional)
            </label>
            <Input
              id="upload-camera-name"
              value={cameraName}
              onChange={(e) => setCameraName(e.target.value)}
              placeholder="e.g. Front Entrance"
              disabled={state === 'uploading'}
              className={FIELD_CLASSES}
            />
          </div>

          <div className="rounded-md border border-warning/20 bg-warning/[0.06] p-2.5 flex items-start gap-2.5 text-[11px] text-warning/80 font-mono">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5 text-warning" />
            <span>
              No spatial calibration matrix linked. Metric velocity and boundary breach events will be
              suppressed; object tracking remains active.
            </span>
          </div>

          {state === 'error' && error && (
            <div role="alert" className="flex items-start gap-2 rounded-md border border-danger bg-danger/10 px-3 py-2 text-xs text-danger">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex items-center justify-end gap-2.5 pt-4 mt-2 border-t border-border">
            <Button
              type="button"
              variant="ghost"
              onClick={handleClose}
              disabled={state === 'uploading'}
              className="font-mono text-xs text-ink-subtle hover:text-ink hover:bg-transparent px-3 py-1.5"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!file || !cameraId.trim() || state === 'uploading'}
              className="gap-1.5 bg-accent hover:bg-accent/90 text-primary font-mono font-semibold text-xs px-4 py-1.5 shadow-sm"
            >
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
