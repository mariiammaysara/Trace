import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { VisionAgentView } from './VisionAgentView'
import * as api from '@/lib/api'

const realEvent = {
  id: 42,
  object_id: 134,
  camera_id: 'demo-trafficlight',
  event_type: 'LINE_CROSSED',
  class_name: 'car',
  timestamp: 9.5,
  confidence: 0.49,
  metadata: {},
  zone_id: null,
  line_id: 'crosswalk_tripwire',
}

describe('VisionAgentView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('sends the real question to POST /agent/query and renders the real answer plus tool calls', async () => {
    vi.spyOn(api, 'queryAgent').mockResolvedValue({
      answer: 'Yes, a vehicle crossed the line.\n\n- Object ID: 134\n- Class: car',
      tool_calls: [{ name: 'get_camera_events', arguments: { camera_id: 'demo-trafficlight' }, result: { events: [] } }],
    })

    render(<VisionAgentView />)

    fireEvent.click(screen.getByText('Show events for camera demo.'))

    expect(api.queryAgent).toHaveBeenCalledWith('Show events for camera demo.')
    expect(screen.getByText('Reasoning over TRACE data…')).toBeInTheDocument()

    await waitFor(() => expect(screen.getByText('Yes, a vehicle crossed the line.')).toBeInTheDocument())
    expect(screen.getByText('Object ID: 134')).toBeInTheDocument()
    expect(screen.getByText('get_camera_events(camera_id="demo-trafficlight")')).toBeInTheDocument()
  })

  it('expands a tool call pill to show the real JSON result', async () => {
    vi.spyOn(api, 'queryAgent').mockResolvedValue({
      answer: 'No matching events were found.',
      tool_calls: [{ name: 'get_traffic_stats', arguments: { camera_id: 'demo' }, result: { traffic_volume: 3 } }],
    })

    render(<VisionAgentView />)
    fireEvent.click(screen.getByText("What's the traffic volume for camera demo?"))

    await waitFor(() => expect(screen.getByText(/get_traffic_stats/)).toBeInTheDocument())
    expect(screen.queryByText(/"traffic_volume": 3/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByText(/get_traffic_stats/))
    expect(screen.getByText(/"traffic_volume": 3/)).toBeInTheDocument()
  })

  it('shows a real incident chip when a tool result carries actual events, and replays it via onReplayEvent', async () => {
    vi.spyOn(api, 'queryAgent').mockResolvedValue({
      answer: 'Yes -- object #134 crossed the tripwire at t=9.5s.',
      tool_calls: [{ name: 'get_camera_events', arguments: { camera_id: 'demo-trafficlight' }, result: { events: [realEvent] } }],
    })
    const onReplayEvent = vi.fn()

    render(<VisionAgentView onReplayEvent={onReplayEvent} />)
    fireEvent.click(screen.getByText('Show events for camera demo.'))

    await waitFor(() => expect(screen.getByText('Related incidents (1)')).toBeInTheDocument())
    expect(screen.getByText('t=9.5s')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Replay incident at 9.5 seconds/i }))
    expect(onReplayEvent).toHaveBeenCalledWith(realEvent)
  })

  it('does not show a "Related incidents" section when no tool result carried real events', async () => {
    vi.spyOn(api, 'queryAgent').mockResolvedValue({
      answer: 'No matching events were found.',
      tool_calls: [{ name: 'get_traffic_stats', arguments: { camera_id: 'demo' }, result: { traffic_volume: 0 } }],
    })

    render(<VisionAgentView onReplayEvent={vi.fn()} />)
    fireEvent.click(screen.getByText("What's the traffic volume for camera demo?"))

    await waitFor(() => expect(screen.getByText('No matching events were found.')).toBeInTheDocument())
    expect(screen.queryByText(/Related incidents/)).not.toBeInTheDocument()
  })

  it('shows the real error (e.g. a 503 for no LLM key configured) honestly, not a fabricated fallback answer', async () => {
    vi.spyOn(api, 'queryAgent').mockRejectedValue(new Error('503: no LLM API key configured'))

    render(<VisionAgentView />)
    fireEvent.click(screen.getByText('Show events for camera demo.'))

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('503: no LLM API key configured'))
  })
})
