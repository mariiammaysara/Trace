import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { EventsView } from './EventsView'
import * as api from '@/lib/api'

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
  last_seen: 50,
}

const mockTrajectory: api.Trajectory = {
  object_id: 1,
  camera_id: 'demo',
  class_name: 'person',
  first_seen: 0,
  last_seen: 50,
  points: [],
}

const mockEvents: api.TraceEvent[] = [
  {
    id: 1,
    object_id: 1,
    event_type: 'OBJECT_APPEARED',
    class_name: 'person',
    timestamp: 5.0,
    confidence: 0.95,
    metadata: {},
    zone_id: null,
    line_id: null,
  },
  {
    id: 2,
    object_id: 1,
    event_type: 'ZONE_ENTERED',
    class_name: 'person',
    timestamp: 42.5,
    confidence: 0.88,
    metadata: {},
    zone_id: 'zone-1',
    line_id: null,
  },
]

function renderEventsView(mode?: 'events' | 'investigation') {
  return render(
    <EventsView cameras={[mockCamera]} selectedCameraId="demo" onSelectCamera={vi.fn()} mode={mode} />,
  )
}

describe('EventsView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'listVideos').mockResolvedValue([mockVideo])
    vi.spyOn(api, 'listCameraObjects').mockResolvedValue([mockObject])
    vi.spyOn(api, 'getObjectTrajectory').mockResolvedValue(mockTrajectory)
    vi.spyOn(api, 'listCameraEvents').mockResolvedValue(mockEvents)
    vi.spyOn(api, 'listCameraZones').mockResolvedValue([])
    vi.spyOn(api, 'listCameraLines').mockResolvedValue([])
    vi.spyOn(api, 'getVideoStreamUrl').mockReturnValue('http://localhost:8000/videos/1/stream')
  })

  it('renders the events table with real fetched events, not placeholders', async () => {
    renderEventsView()

    expect(await screen.findByText('OBJECT_APPEARED')).toBeInTheDocument()
    expect(screen.getByText('ZONE_ENTERED')).toBeInTheDocument()
    expect(screen.getByText('5.0s')).toBeInTheDocument()
    expect(screen.getByText('42.5s')).toBeInTheDocument()
    expect(screen.getAllByText('#1')).toHaveLength(2)
    expect(screen.getByText('95%')).toBeInTheDocument()
    expect(screen.getByText('88%')).toBeInTheDocument()
  })

  it('renders badge colors in the table matching the documented event->color mapping', async () => {
    renderEventsView()

    const violationBadge = await screen.findByText('ZONE_ENTERED')
    expect(violationBadge).toHaveClass('text-danger')

    const lifecycleBadge = screen.getByText('OBJECT_APPEARED')
    expect(lifecycleBadge).toHaveClass('text-info')
    expect(lifecycleBadge).not.toHaveClass('text-danger')
  })

  it('clicking a row seeks the shared video player to that event\'s timestamp', async () => {
    const user = userEvent.setup()
    renderEventsView()

    await screen.findByText('ZONE_ENTERED')
    // Player starts at 0.0s before any row is clicked.
    expect(screen.getByText(/^0\.0s \//)).toBeInTheDocument()

    const zoneEnteredRow = screen.getByText('ZONE_ENTERED').closest('tr')
    expect(zoneEnteredRow).not.toBeNull()
    await user.click(zoneEnteredRow as HTMLElement)

    await waitFor(() => expect(screen.getByText(/^42\.5s \//)).toBeInTheDocument())
  })

  it('filters events by event type through the API rather than client-side only', async () => {
    const user = userEvent.setup()
    renderEventsView()

    await screen.findByText('ZONE_ENTERED')
    vi.mocked(api.listCameraEvents).mockClear()

    const combobox = screen.getAllByRole('combobox').find((el) => el.id === 'event-type-filter')
    expect(combobox).toBeDefined()
    await user.click(combobox as HTMLElement)
    const option = await screen.findByRole('option', { name: 'ZONE_ENTERED' })
    await user.click(option)

    await waitFor(() =>
      expect(api.listCameraEvents).toHaveBeenCalledWith('demo', expect.objectContaining({ eventType: 'ZONE_ENTERED' })),
    )
  })

  it('shows an error message if the camera scene fetch fails', async () => {
    vi.spyOn(api, 'listVideos').mockRejectedValue(new Error('network down'))

    renderEventsView()

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('network down'))
  })

  it('investigation mode shows an empty prompt until an event is selected, then the evidence panel', async () => {
    const user = userEvent.setup()
    renderEventsView('investigation')

    expect(screen.getByText(/Select an event to begin investigating/i)).toBeInTheDocument()

    const zoneEnteredRow = (await screen.findAllByText('ZONE_ENTERED'))[0].closest('[role="button"]')
    expect(zoneEnteredRow).not.toBeNull()
    await user.click(zoneEnteredRow as HTMLElement)

    await waitFor(() => expect(api.getObjectTrajectory).toHaveBeenCalledWith(1))
    expect(screen.getByText('Trajectory')).toBeInTheDocument()
    expect(screen.getByText('Related events')).toBeInTheDocument()
  })
})
