import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { DemoScenariosModal } from '@/components/DemoScenariosModal'
import { LiveIncidentBanner } from '@/components/LiveIncidentBanner'
import { DEMO_SCENARIOS } from '@/lib/demoScenarios'
import type { TraceEvent } from '@/lib/api'

describe('Phase 20: Demo Scenarios Modal', () => {
  it('renders all real pre-recorded demo scenarios and transparency note', () => {
    render(
      <DemoScenariosModal
        isOpen={true}
        onClose={vi.fn()}
        onLaunchScenario={vi.fn()}
      />,
    )

    expect(screen.getByText('Demo Scenarios')).toBeInTheDocument()
    expect(screen.getByText('Street Corner Vehicle Line Crossing')).toBeInTheDocument()
    expect(screen.getByText(/Footprint transparency/i)).toBeInTheDocument()
  })

  it('launches a selected scenario with the correct camera, video, and start timestamp', () => {
    const handleLaunch = vi.fn()
    const handleClose = vi.fn()

    render(
      <DemoScenariosModal
        isOpen={true}
        onClose={handleClose}
        onLaunchScenario={handleLaunch}
      />,
    )

    const launchButtons = screen.getAllByRole('button', { name: /Launch Scenario/i })
    expect(launchButtons.length).toBe(1)

    // Launch the only remaining scenario (Street Corner Vehicle Line Crossing)
    fireEvent.click(launchButtons[0])

    expect(handleLaunch).toHaveBeenCalledWith(DEMO_SCENARIOS[0])
    expect(handleClose).toHaveBeenCalledTimes(1)
  })
})

describe('Phase 20: Live Incident Banner (In-Demo Real-Event Surfacing)', () => {
  const mockEvents: TraceEvent[] = [
    {
      id: 42,
      object_id: 1,
      event_type: 'ZONE_ENTERED',
      class_name: 'person',
      timestamp: 2.5,
      confidence: 0.95,
      metadata: { zone_id: 'restricted_area' },
      zone_id: 'restricted_area',
      line_id: null,
    },
    {
      id: 43,
      object_id: 1,
      event_type: 'LINE_CROSSED',
      class_name: 'person',
      timestamp: 5.0,
      confidence: 0.92,
      metadata: { line_id: 'entrance_line', direction: 'A_to_B' },
      zone_id: null,
      line_id: 'entrance_line',
    },
  ]

  it('surfaces real event when video playback reaches its timestamp', () => {
    const handleInvestigate = vi.fn()

    const { rerender } = render(
      <LiveIncidentBanner
        currentTime={0.0}
        events={mockEvents}
        onInvestigateEvent={handleInvestigate}
        activeScenarioTitle="Restricted Area Breach"
      />,
    )

    // At t=0.0s, no event is active
    expect(screen.queryByRole('region', { name: /Real-time event notification/i })).not.toBeInTheDocument()

    // Playback advances to t=2.5s (matching ZONE_ENTERED event #42)
    rerender(
      <LiveIncidentBanner
        currentTime={2.5}
        events={mockEvents}
        onInvestigateEvent={handleInvestigate}
        activeScenarioTitle="Restricted Area Breach"
      />,
    )

    // Phase 21: redesigned as a compact corner HUD (item 3) -- event type,
    // target, and timestamp stay visible text; the scenario title becomes a
    // hover tooltip (title attribute) rather than its own visible badge, to
    // keep the footprint small.
    const notification = screen.getByRole('region', { name: /Real-time event notification/i })
    expect(notification).toBeInTheDocument()
    expect(notification).toHaveAttribute('title', 'Restricted Area Breach')
    expect(screen.getByText('ZONE_ENTERED')).toBeInTheDocument()
    expect(screen.getByText(/#1 person/i)).toBeInTheDocument()

    // Clicking Investigate calls handler with the real event id
    const investigateBtn = screen.getByRole('button', { name: /Investigate/i })
    fireEvent.click(investigateBtn)
    expect(handleInvestigate).toHaveBeenCalledWith(42)
  })

  it('does not trigger on scripted or non-existent events', () => {
    render(
      <LiveIncidentBanner
        currentTime={99.9}
        events={mockEvents}
        onInvestigateEvent={vi.fn()}
      />,
    )

    expect(screen.queryByRole('region', { name: /Real-time event notification/i })).not.toBeInTheDocument()
  })
})
