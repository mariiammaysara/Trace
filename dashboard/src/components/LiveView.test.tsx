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

const otherCamera: api.Camera = {
  id: 2,
  camera_id: 'demo-trafficlight',
  name: 'Trafficlight Camera',
  location: null,
  calibration_reference: null,
}

const mockZone: api.Zone = { id: 1, zone_id: 'restricted_area', polygon: [[0, 0], [1, 0], [1, 1], [0, 1]] }
const mockLine: api.Line = { id: 1, line_id: 'entrance_line', start: [0, 0], end: [1, 1] }
const mockEvent: api.TraceEvent = {
  id: 1,
  object_id: 1,
  event_type: 'OBJECT_APPEARED',
  class_name: 'person',
  timestamp: 0,
  confidence: 0.9,
  metadata: {},
  zone_id: null,
  line_id: null,
}

describe('LiveView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'listVideos').mockResolvedValue([mockVideo])
    vi.spyOn(api, 'listCameraObjects').mockResolvedValue([mockObject])
    vi.spyOn(api, 'getObjectTrajectory').mockResolvedValue(mockTrajectory)
    vi.spyOn(api, 'listCameraEvents').mockResolvedValue([])
    vi.spyOn(api, 'listCameraZones').mockResolvedValue([])
    vi.spyOn(api, 'listCameraLines').mockResolvedValue([])
    vi.spyOn(api, 'getVideoStreamUrl').mockReturnValue('http://localhost:8000/videos/1/stream')
  })

  it('renders the camera switcher and video for the selected camera', async () => {
    render(<LiveView cameras={[mockCamera]} selectedCameraId="demo" onSelectCamera={vi.fn()} />)

    expect(screen.getByText('Demo Camera')).toBeInTheDocument()

    await waitFor(() => expect(screen.getByRole('button', { name: 'Play' })).toBeInTheDocument())

    const video = document.querySelector('video')
    expect(video).not.toBeNull()
    expect(video).toHaveAttribute('src', 'http://localhost:8000/videos/1/stream')

    expect(api.listCameraObjects).toHaveBeenCalledWith('demo')
    expect(api.getObjectTrajectory).toHaveBeenCalledWith(1)
  })

  it('shows an error message if the camera scene fetch fails', async () => {
    vi.spyOn(api, 'listVideos').mockRejectedValue(new Error('network down'))

    render(<LiveView cameras={[mockCamera]} selectedCameraId="demo" onSelectCamera={vi.fn()} />)

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('network down'))
  })

  it('shows a no-video message when the camera has none registered', async () => {
    vi.spyOn(api, 'listVideos').mockResolvedValue([])

    render(<LiveView cameras={[mockCamera]} selectedCameraId="demo" onSelectCamera={vi.fn()} />)

    await waitFor(() => expect(screen.getByText(/No video registered/i)).toBeInTheDocument())
  })

  it('shows an empty state when no cameras are registered', () => {
    render(<LiveView cameras={[]} selectedCameraId={null} onSelectCamera={vi.fn()} />)

    expect(screen.getByText(/No cameras registered/i)).toBeInTheDocument()
  })

  // Regression test for the item-1 bug: useCameraScene reset `video` and
  // `trajectories` synchronously on a camera switch, but left `events`,
  // `zones`, and `lines` holding the PREVIOUS camera's values until the new
  // fetch resolved -- so those three stayed stale (and inconsistent with the
  // rest of the page, which had already moved on) for as long as the new
  // camera's request was in flight.
  it('does not show the previous camera\'s zones/lines/events while the new camera\'s data is still loading', async () => {
    vi.spyOn(api, 'listCameraZones').mockResolvedValueOnce([mockZone])
    vi.spyOn(api, 'listCameraLines').mockResolvedValueOnce([mockLine])
    vi.spyOn(api, 'listCameraEvents').mockResolvedValueOnce([mockEvent])

    const { rerender } = render(
      <LiveView cameras={[mockCamera, otherCamera]} selectedCameraId="demo" onSelectCamera={vi.fn()} />,
    )

    await waitFor(() => expect(screen.getByText('Zones').nextSibling).toHaveTextContent('1'))
    expect(screen.getByText('Lines').nextSibling).toHaveTextContent('1')
    expect(screen.getByText('Events').nextSibling).toHaveTextContent('1')

    // Switch cameras, holding the new camera's video fetch open so we can
    // inspect state in the window between the switch and the new data
    // actually arriving.
    let resolveVideos: (videos: api.Video[]) => void = () => {}
    vi.spyOn(api, 'listVideos').mockReturnValueOnce(
      new Promise<api.Video[]>((resolve) => {
        resolveVideos = resolve
      }),
    )

    rerender(
      <LiveView cameras={[mockCamera, otherCamera]} selectedCameraId="demo-trafficlight" onSelectCamera={vi.fn()} />,
    )

    // Immediately after switching -- before the new camera's fetch resolves
    // -- nothing should still show camera "demo"'s zone/line/event counts.
    expect(screen.getByText('Zones').nextSibling).toHaveTextContent('0')
    expect(screen.getByText('Lines').nextSibling).toHaveTextContent('0')
    expect(screen.getByText('Events').nextSibling).toHaveTextContent('0')

    resolveVideos([mockVideo])
    await waitFor(() => expect(api.listCameraZones).toHaveBeenCalledWith('demo-trafficlight'))
  })
})
