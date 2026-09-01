import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AnalyticsView } from './AnalyticsView'
import * as api from '@/lib/api'

const mockCamera: api.Camera = {
  id: 1,
  camera_id: 'demo',
  name: 'Demo Camera',
  location: null,
  calibration_reference: null,
}

const mockAnalytics: api.AnalyticsSummary = {
  camera_id: 'demo',
  start_time: null,
  end_time: null,
  object_count: 5,
  line_crossing_count: 3,
  zone_violation_count: 2,
  average_dwell_time: 4.5,
  traffic_volume: 1,
  event_frequency: { ZONE_ENTERED: 2, OBJECT_APPEARED: 5 },
  per_class_stats: { person: { object_count: 5, event_count: 7 } },
}

const mockEvents: api.TraceEvent[] = [
  {
    id: 1,
    object_id: 1,
    event_type: 'ZONE_ENTERED',
    class_name: 'person',
    timestamp: 12.5,
    confidence: 0.9,
    metadata: {},
    zone_id: 'zone-1',
    line_id: null,
  },
]

describe('AnalyticsView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'listCameras').mockResolvedValue([mockCamera])
    vi.spyOn(api, 'getAnalytics').mockResolvedValue(mockAnalytics)
    vi.spyOn(api, 'listCameraEvents').mockResolvedValue(mockEvents)
  })

  it('renders real fetched analytics data in the stat cards', async () => {
    render(<AnalyticsView />)

    await waitFor(() => expect(api.getAnalytics).toHaveBeenCalledWith('demo'))

    expect(await screen.findByTestId('stat-value-Objects tracked')).toHaveTextContent('5')
    expect(screen.getByTestId('stat-value-Line crossings')).toHaveTextContent('3')
    expect(screen.getByTestId('stat-value-Zone violations')).toHaveTextContent('2')
    expect(screen.getByTestId('stat-value-Traffic volume')).toHaveTextContent('1')
    expect(screen.getByTestId('stat-value-Avg. dwell time')).toHaveTextContent('4.5s')
  })

  it('renders the zone-violations stat in --color-danger, not the default brand color', async () => {
    render(<AnalyticsView />)

    const value = await screen.findByTestId('stat-value-Zone violations')
    expect(value).toHaveClass('text-danger')
    expect(value).not.toHaveClass('text-primary')

    const normalValue = screen.getByTestId('stat-value-Objects tracked')
    expect(normalValue).toHaveClass('text-primary')
    expect(normalValue).not.toHaveClass('text-danger')
  })

  it('renders the ZONE_ENTERED event-frequency bar in danger, not accent', async () => {
    render(<AnalyticsView />)

    const bar = await screen.findByTestId('bar-ZONE_ENTERED')
    expect(bar).toHaveClass('bg-danger')

    const normalBar = screen.getByTestId('bar-OBJECT_APPEARED')
    expect(normalBar).toHaveClass('bg-accent')
    expect(normalBar).not.toHaveClass('bg-danger')
  })

  it('shows an error message if the initial camera fetch fails', async () => {
    vi.spyOn(api, 'listCameras').mockRejectedValue(new Error('network down'))

    render(<AnalyticsView />)

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('network down'))
  })
})
