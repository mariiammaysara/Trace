import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LiveView } from './LiveView'
import * as api from '@/lib/api'

// jsdom doesn't implement HTMLMediaElement.play/pause -- calling them throws
// "Not implemented". LiveView never calls play() on its own (only in
// response to a user click), but the element still renders <video>, whose
// presence alone is enough for this test's purpose.
Object.defineProperty(window.HTMLMediaElement.prototype, 'play', {
  configurable: true,
  value: vi.fn().mockResolvedValue(undefined),
})
Object.defineProperty(window.HTMLMediaElement.prototype, 'pause', {
  configurable: true,
  value: vi.fn(),
})

const mockCamera: api.Camera = {
  id: 1,
  camera_id: 'demo',
  name: 'Demo Camera',
  location: null,
  calibration_reference: null,
}

const mockVideo: api.Video = { id: 1, camera_id: 1, path: 'data/sample.mp4', started_at: null }

const mockObject: api.TrackedObjectSummary = {
  id: 1,
  object_id: 1,
  class_name: 'person',
  first_seen: 0,
  last_seen: 10,
}

const mockTrajectory: api.Trajectory = {
  object_id: 1,
  camera_id: 'demo',
  class_name: 'person',
  first_seen: 0,
  last_seen: 10,
  points: [{ frame_id: 0, timestamp: 0, x: 10, y: 10, x_min: 0, y_min: 0, x_max: 20, y_max: 20 }],
}

describe('LiveView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'listCameras').mockResolvedValue([mockCamera])
    vi.spyOn(api, 'listVideos').mockResolvedValue([mockVideo])
    vi.spyOn(api, 'listCameraObjects').mockResolvedValue([mockObject])
    vi.spyOn(api, 'getObjectTrajectory').mockResolvedValue(mockTrajectory)
    vi.spyOn(api, 'listCameraEvents').mockResolvedValue([])
    vi.spyOn(api, 'listCameraZones').mockResolvedValue([])
    vi.spyOn(api, 'listCameraLines').mockResolvedValue([])
    vi.spyOn(api, 'getVideoStreamUrl').mockReturnValue('http://localhost:8000/videos/1/stream')
  })

  it('renders the camera selector and video from a mocked API response', async () => {
    render(<LiveView />)

    await waitFor(() => expect(api.listCameras).toHaveBeenCalled())
    // The trigger shows the raw camera_id ("demo"), not the display name,
    // until the dropdown is actually opened and the matching SelectItem
    // mounts -- Base UI only resolves an item's label once it's been
    // rendered at least once. Proof the right camera got auto-selected is
    // this value reaching the trigger and flowing into the API calls below,
    // not the label text (which needs a real open-dropdown interaction).
    await waitFor(() => expect(screen.getByRole('combobox')).toHaveTextContent('demo'))

    await waitFor(() => expect(screen.getByRole('button', { name: 'Play' })).toBeInTheDocument())

    const video = document.querySelector('video')
    expect(video).not.toBeNull()
    expect(video).toHaveAttribute('src', 'http://localhost:8000/videos/1/stream')

    expect(api.listCameraObjects).toHaveBeenCalledWith('demo')
    expect(api.getObjectTrajectory).toHaveBeenCalledWith(1)
  })

  it('shows an error message if the initial camera fetch fails', async () => {
    vi.spyOn(api, 'listCameras').mockRejectedValue(new Error('network down'))

    render(<LiveView />)

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('network down'))
  })

  it('shows a no-video message when the camera has none registered', async () => {
    vi.spyOn(api, 'listVideos').mockResolvedValue([])

    render(<LiveView />)

    await waitFor(() => expect(screen.getByText(/No video registered/i)).toBeInTheDocument())
  })
})
