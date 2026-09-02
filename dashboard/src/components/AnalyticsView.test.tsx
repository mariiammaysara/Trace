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

function renderAnalyticsView() {
  return render(<AnalyticsView cameras={[mockCamera]} selectedCameraId="demo" onSelectCamera={vi.fn()} />)
}

describe('AnalyticsView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'getAnalytics').mockResolvedValue(mockAnalytics)
    vi.spyOn(api, 'listCameraEvents').mockResolvedValue(mockEvents)
  })

  it('renders real fetched analytics data in the metrics strip', async () => {
    renderAnalyticsView()

    await waitFor(() => expect(api.getAnalytics).toHaveBeenCalledWith('demo'))

    expect(await screen.findByTestId('metric-objects-tracked')).toHaveTextContent('5')
    expect(screen.getByTestId('metric-line-crossings')).toHaveTextContent('3')
    expect(screen.getByTestId('metric-zone-violations')).toHaveTextContent('2')
    expect(screen.getByTestId('metric-traffic-volume')).toHaveTextContent('1')
    expect(screen.getByTestId('metric-avg-dwell')).toHaveTextContent('4.5s')
  })

  it('renders the zone-violations metric in --color-danger, not the default ink color', async () => {
    renderAnalyticsView()

    const value = await screen.findByTestId('metric-zone-violations')
    expect(value).toHaveClass('text-danger')
    expect(value).not.toHaveClass('text-ink')

    const normalValue = screen.getByTestId('metric-objects-tracked')
    expect(normalValue).toHaveClass('text-ink')
    expect(normalValue).not.toHaveClass('text-danger')
  })

  it('renders the ZONE_ENTERED event-frequency bar in danger, not accent', async () => {
    renderAnalyticsView()

    const bar = await screen.findByTestId('bar-ZONE_ENTERED')
    expect(bar).toHaveClass('bg-danger')

    const normalBar = screen.getByTestId('bar-OBJECT_APPEARED')
    expect(normalBar).toHaveClass('bg-accent')
    expect(normalBar).not.toHaveClass('bg-danger')
  })

  it('shows an error message if the analytics fetch fails', async () => {
    vi.spyOn(api, 'getAnalytics').mockRejectedValue(new Error('network down'))

    renderAnalyticsView()

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('network down'))
  })
})
