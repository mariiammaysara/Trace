import { useEffect, useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { VideoPlayer } from '@/components/VideoPlayer'
import { listCameras } from '@/lib/api'
import type { Camera } from '@/lib/api'
import { useCameraScene } from '@/hooks/useCameraScene'

/**
 * The Live/Video dashboard view: real video playback with detection boxes,
 * track IDs, trajectories, zones, and lines overlaid via VideoPlayer's
 * player + VideoOverlay's SVG layer, synced to playback -- never baked into
 * the video file. Every value shown comes from the Phase 9/10 API
 * (src/lib/api.ts, src/hooks/useCameraScene.ts); nothing here is
 * mock/hardcoded data.
 */
export function LiveView() {
  const [cameras, setCameras] = useState<Camera[]>([])
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null)
  const [camerasError, setCamerasError] = useState<string | null>(null)

  useEffect(() => {
    listCameras()
      .then((result) => {
        setCameras(result)
        setSelectedCameraId((current) => current ?? result[0]?.camera_id ?? null)
      })
      .catch((err: unknown) => setCamerasError(String(err)))
  }, [])

  const { video, trajectories, events, zones, lines, error: sceneError } = useCameraScene(selectedCameraId)
  const error = camerasError ?? sceneError

  return (
    <div className="flex flex-col gap-4">
      {/* value is intentionally `selectedCameraId` (string | null), never
          coerced to `undefined` -- Base UI's Select treats `undefined` as
          "uncontrolled" and `null` as "controlled, nothing selected yet".
          Passing `undefined` here on the first render (before cameras load)
          would flip the component from uncontrolled to controlled the
          moment a camera loads, which Base UI warns about and which broke
          the displayed value actually updating. */}
      <Select value={selectedCameraId} onValueChange={(value) => setSelectedCameraId(value)}>
        <SelectTrigger className="w-56">
          <SelectValue placeholder="Select a camera" />
        </SelectTrigger>
        <SelectContent>
          {cameras.map((camera) => (
            <SelectItem key={camera.camera_id} value={camera.camera_id}>
              {camera.name ?? camera.camera_id}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {error && (
        <div role="alert" className="rounded-md border border-danger bg-danger/10 px-4 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      {video ? (
        <VideoPlayer video={video} trajectories={trajectories} events={events} zones={zones} lines={lines} />
      ) : (
        !error && <p className="text-secondary">No video registered for this camera yet.</p>
      )}
    </div>
  )
}
