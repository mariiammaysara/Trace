import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { deleteCamera, getCameraDeletionPreview } from '@/lib/api'
import type { CameraDeletionCounts } from '@/lib/api'
import { AlertTriangle, Loader2, ShieldAlert, Trash2, X } from 'lucide-react'

interface DeleteCameraDialogProps {
  /** null closes the dialog. Passing a new camera_id re-opens it and
   * re-fetches that camera's own real preview counts from scratch. */
  cameraId: string | null
  onClose: () => void
  onDeleted: (cameraId: string, deleted: CameraDeletionCounts) => void
}

type Phase = 'loading' | 'ready' | 'deleting' | 'error'

/** These two are cited by name (event counts, the LINE_CROSSED example,
 * evaluation numbers) in README.md and TRACE_STUDY_GUIDE.md -- deleting
 * either one desyncs the live dashboard from the written documentation
 * until it's re-seeded. Not blocked, just gated behind a harder-to-
 * accidentally-trigger confirmation than every other camera gets. */
const REFERENCE_CAMERA_IDS = new Set(['demo', 'demo-trafficlight'])

const COUNT_LABELS: { key: keyof CameraDeletionCounts; label: string }[] = [
  { key: 'events', label: 'Events' },
  { key: 'objects', label: 'Tracked objects' },
  { key: 'track_points', label: 'Track points' },
  { key: 'videos', label: 'Videos' },
  { key: 'alerts', label: 'Alerts' },
  { key: 'zones', label: 'Zones' },
  { key: 'lines', label: 'Lines' },
]

/**
 * Shared delete-confirmation dialog -- one instance, opened from either
 * Camera Fleet (CamerasView) or Recent Uploads (RecentUploadsPanel), since
 * both ultimately delete the same real resource (a camera and its full FK
 * graph, DELETE /cameras/{camera_id}). Preview counts are always fetched
 * fresh from the real backend (GET .../deletion-preview) before showing the
 * confirmation -- never a guessed/estimated number.
 */
export function DeleteCameraDialog({ cameraId, onClose, onDeleted }: DeleteCameraDialogProps) {
  const [phase, setPhase] = useState<Phase>('loading')
  const [counts, setCounts] = useState<CameraDeletionCounts | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [typedConfirmation, setTypedConfirmation] = useState('')

  const isReferenceCamera = cameraId !== null && REFERENCE_CAMERA_IDS.has(cameraId)

  useEffect(() => {
    if (cameraId === null) return
    setPhase('loading')
    setCounts(null)
    setError(null)
    setTypedConfirmation('')

    let cancelled = false
    getCameraDeletionPreview(cameraId)
      .then((result) => {
        if (cancelled) return
        setCounts(result)
        setPhase('ready')
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(String(err instanceof Error ? err.message : err))
        setPhase('error')
      })

    return () => {
      cancelled = true
    }
  }, [cameraId])

  if (cameraId === null) return null

  const typedConfirmationSatisfied = !isReferenceCamera || typedConfirmation === cameraId
  // Written as `phase !== 'ready'`, not a named `phase === 'ready'` alias --
  // TS's aliased-condition narrowing otherwise infers `phase` can only be
  // 'ready' anywhere an alias like that is checked, which then flags the
  // real `phase === 'deleting'` comparisons elsewhere in this component as
  // impossible comparisons.
  const notReadyToConfirm = phase !== 'ready' || !typedConfirmationSatisfied

  async function handleConfirm() {
    if (notReadyToConfirm || cameraId === null) return
    setPhase('deleting')
    setError(null)
    try {
      const deleted = await deleteCamera(cameraId)
      onDeleted(cameraId, deleted)
      onClose()
    } catch (err: unknown) {
      setError(String(err instanceof Error ? err.message : err))
      setPhase('error')
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-camera-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-primary/70 backdrop-blur-md p-4"
    >
      <div className="relative flex w-full max-w-md flex-col rounded-xl border border-border bg-surface shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between border-b border-border px-5 py-4 bg-surface-alt/40">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-danger/10 text-danger">
              <Trash2 className="h-4 w-4" />
            </div>
            <div>
              <h2 id="delete-camera-title" className="text-base font-semibold text-ink leading-tight">
                Delete camera
              </h2>
              <p className="text-xs font-mono text-ink-subtle">{cameraId}</p>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            disabled={phase === 'deleting'}
            aria-label="Close delete confirmation"
            className="text-ink-subtle hover:text-ink"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex flex-col gap-3.5 p-5">
          {phase === 'loading' && (
            <div className="flex items-center gap-2 text-xs text-ink-subtle">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Checking what would be deleted…
            </div>
          )}

          {counts && (
            <div className="flex flex-col gap-1.5">
              <p className="text-xs text-ink-subtle">This permanently deletes this camera and:</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 rounded-md border border-border bg-surface-alt/40 p-3">
                {COUNT_LABELS.map(({ key, label }) => (
                  <div key={key} className="flex items-center justify-between gap-2 text-xs">
                    <span className="text-ink-subtle">{label}</span>
                    <span className="font-mono font-semibold text-ink">{counts[key]}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {isReferenceCamera && (
            <div className="flex items-start gap-2.5 rounded-md border border-danger/30 bg-danger/10 p-3 text-xs text-danger">
              <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
              <div className="flex flex-col gap-1.5">
                <p className="font-semibold">This is one of TRACE's documented reference cameras.</p>
                <p className="leading-relaxed">
                  Its event counts, the LINE_CROSSED example, and evaluation numbers are cited by name in
                  README.md and TRACE_STUDY_GUIDE.md. Deleting it will not update those documents -- the live
                  dashboard will stop matching the written documentation until this camera is re-seeded.
                </p>
                <label htmlFor="delete-camera-confirm-name" className="mt-1 flex flex-col gap-1">
                  <span className="text-[11px] font-mono uppercase tracking-wide text-danger/80">
                    Type "{cameraId}" to confirm
                  </span>
                  <Input
                    id="delete-camera-confirm-name"
                    value={typedConfirmation}
                    onChange={(e) => setTypedConfirmation(e.target.value)}
                    disabled={phase === 'deleting'}
                    placeholder={cameraId}
                    className="border-danger/40 bg-surface font-mono text-xs text-ink focus-visible:border-danger"
                  />
                </label>
              </div>
            </div>
          )}

          {phase === 'error' && error && (
            <div role="alert" className="flex items-start gap-2 rounded-md border border-danger bg-danger/10 px-3 py-2 text-xs text-danger">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-1">
            <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={phase === 'deleting'}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              size="sm"
              onClick={handleConfirm}
              disabled={notReadyToConfirm}
              className="gap-1.5"
            >
              {phase === 'deleting' ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Deleting…
                </>
              ) : (
                <>
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete camera
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
