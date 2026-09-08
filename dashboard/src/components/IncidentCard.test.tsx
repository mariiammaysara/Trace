import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { IncidentCard } from './IncidentCard'
import type { TraceEvent } from '@/lib/api'

const mockEvent: TraceEvent = {
  id: 42,
  object_id: 134,
  event_type: 'LINE_CROSSED',
  class_name: 'car',
  timestamp: 9.5,
  confidence: 0.87,
  metadata: {},
  zone_id: null,
  line_id: 'crosswalk_tripwire',
}

describe('IncidentCard', () => {
  it('renders timestamp, event type (colored by real severity), and target id/class on one line', () => {
    render(<IncidentCard event={mockEvent} />)

    expect(screen.getByText('9.5s')).toBeInTheDocument()
    const eventType = screen.getByText('LINE_CROSSED')
    expect(eventType).toHaveClass('text-danger')
    expect(screen.getByText('#134')).toBeInTheDocument()
    expect(screen.getByText(/car/)).toBeInTheDocument()
  })

  it('colors a warning-tier event type differently from a danger-tier one', () => {
    render(<IncidentCard event={{ ...mockEvent, event_type: 'LOITERING' }} />)
    expect(screen.getByText('LOITERING')).not.toHaveClass('text-danger')
  })

  it('calls onSelect when the row is clicked', () => {
    const onSelect = vi.fn()
    render(<IncidentCard event={mockEvent} onSelect={onSelect} />)

    const row = screen.getByText('9.5s').closest('[role="button"]')
    expect(row).not.toBeNull()
    fireEvent.click(row as HTMLElement)
    expect(onSelect).toHaveBeenCalledWith(mockEvent)
  })

  it('calls onSelect (the seek action) when the Replay button is clicked, without a double invocation from row bubbling', () => {
    const onSelect = vi.fn()
    render(<IncidentCard event={mockEvent} onSelect={onSelect} />)

    fireEvent.click(screen.getByRole('button', { name: /Replay incident at 9.5 seconds/i }))
    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith(mockEvent)
  })
})
