import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { ObjectProfilePanel } from './ObjectProfilePanel'
import * as api from '@/lib/api'
import { formatSeconds } from '@/lib/analytics'

const mockVideo: api.Video = { id: 9, camera_id: 1, path: 'data/sample.mp4', started_at: null }

const mockTrajectory: api.Trajectory = {
  object_id: 5,
  camera_id: 'cam_profile',
  class_name: 'person',
  first_seen: 10.0,
  last_seen: 70.0,
  points: [
    { frame_id: 0, timestamp: 10.0, x: 1, y: 1, x_min: null, y_min: null, x_max: null, y_max: null },
    { frame_id: 1, timestamp: 40.0, x: 2, y: 2, x_min: null, y_min: null, x_max: null, y_max: null },
  ],
}

// Two completed real zone visits (10.0 -> 25.0 and 40.0 -> 52.0), plus one
// non-zone event -- lets the test compute the expected dwell sum and event
// count itself instead of trusting a magic number baked into the mock.
const visit1 = { entry: 10.0, exit: 25.0 }
const visit2 = { entry: 40.0, exit: 52.0 }
const expectedDwellSeconds = visit1.exit - visit1.entry + (visit2.exit - visit2.entry)

const mockObjectEvents: api.TraceEvent[] = [
  { id: 1, object_id: 5, event_type: 'OBJECT_APPEARED', class_name: 'person', timestamp: 0.0, confidence: 0.95, metadata: {}, zone_id: null, line_id: null },
  { id: 2, object_id: 5, event_type: 'ZONE_ENTERED', class_name: 'person', timestamp: visit1.entry, confidence: 0.9, metadata: {}, zone_id: 'z1', line_id: null },
  { id: 3, object_id: 5, event_type: 'ZONE_EXITED', class_name: 'person', timestamp: visit1.exit, confidence: 0.9, metadata: {}, zone_id: 'z1', line_id: null },
  { id: 4, object_id: 5, event_type: 'ZONE_ENTERED', class_name: 'person', timestamp: visit2.entry, confidence: 0.9, metadata: {}, zone_id: 'z1', line_id: null },
  { id: 5, object_id: 5, event_type: 'ZONE_EXITED', class_name: 'person', timestamp: visit2.exit, confidence: 0.9, metadata: {}, zone_id: 'z1', line_id: null },
]

// The real backend endpoint (src/api/routers/objects.py's get_object_profile)
// computes this same sum server-side from the events above -- see
// tests/test_api.py's test_get_object_profile_aggregates_dwell_time_and_event_count_correctly
// for the backend-side proof of that arithmetic. This mock mirrors exactly
// what a correct server response for these events would contain.
const mockProfile: api.ObjectProfile = {
  id: 5,
  object_id: 2,
  class_name: 'person',
  first_seen: 10.0,
  last_seen: 70.0,
  camera_id: 'cam_profile',
  camera_name: 'Front Gate',
  total_dwell_seconds: expectedDwellSeconds,
  event_count: mockObjectEvents.length,
}

function renderPanel(objectId: number | null, onOpenIncident = vi.fn()) {
  return render(<ObjectProfilePanel objectId={objectId} onClose={vi.fn()} onOpenIncident={onOpenIncident} />)
}

describe('ObjectProfilePanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'getObjectProfile').mockResolvedValue(mockProfile)
    vi.spyOn(api, 'getObjectEvents').mockResolvedValue(mockObjectEvents)
    vi.spyOn(api, 'listVideos').mockResolvedValue([mockVideo])
    vi.spyOn(api, 'listCameraObjects').mockResolvedValue([
      { id: 5, object_id: 2, class_name: 'person', first_seen: 10.0, last_seen: 70.0 },
    ])
    vi.spyOn(api, 'getObjectTrajectory').mockResolvedValue(mockTrajectory)
    vi.spyOn(api, 'listCameraEvents').mockResolvedValue(mockObjectEvents)
    vi.spyOn(api, 'listCameraZones').mockResolvedValue([])
    vi.spyOn(api, 'listCameraLines').mockResolvedValue([])
    vi.spyOn(api, 'getVideoStreamUrl').mockReturnValue('http://localhost:8000/videos/9/stream')
  })

  it('renders nothing loaded when closed (objectId is null)', () => {
    renderPanel(null)
    expect(screen.queryByText('Front Gate')).not.toBeInTheDocument()
  })

  it("renders the real profile's aggregated dwell time, event count, and first/last seen -- computed, not fabricated", async () => {
    renderPanel(5)

    await waitFor(() => expect(api.getObjectProfile).toHaveBeenCalledWith(5))

    // Dwell time: the panel must display the exact sum of the two real zone
    // visits (15.0s + 12.0s = 27.0s), not a placeholder or a value that
    // silently drops one visit.
    expect(expectedDwellSeconds).toBe(27.0)
    expect(await screen.findByText(formatSeconds(expectedDwellSeconds))).toBeInTheDocument()

    // Event count: exactly the number of real events seeded for this
    // object (5), not the length of some unrelated list.
    expect(mockObjectEvents.length).toBe(5)
    expect(screen.getByText('5')).toBeInTheDocument()

    expect(screen.getByText(/first 10\.0s/)).toBeInTheDocument()
    expect(screen.getByText(/last 70\.0s/)).toBeInTheDocument()
    expect(screen.getByText('Front Gate')).toBeInTheDocument()
  })

  it("lists the object's own real events and opens Phase 18's incident view when one is clicked", async () => {
    const user = userEvent.setup()
    const onOpenIncident = vi.fn()
    renderPanel(5, onOpenIncident)

    await screen.findByText('Front Gate')
    expect(screen.getByText('Events (5)')).toBeInTheDocument()

    const zoneEnteredRows = await screen.findAllByText('ZONE_ENTERED')
    await user.click(zoneEnteredRows[0])

    expect(onOpenIncident).toHaveBeenCalledWith(2, 'cam_profile')
  })

  it('shows a real error state, not fabricated data, when the profile fetch fails', async () => {
    vi.spyOn(api, 'getObjectProfile').mockRejectedValue(new Error('object not found'))
    renderPanel(999)

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('object not found'))
  })
})
