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
  it('renders severity badge, target id/class, and exact timestamp', () => {
    render(<IncidentCard event={mockEvent} />)

    const badge = screen.getByText('LINE_CROSSED')
    expect(badge).toHaveAttribute('data-severity', 'danger')
    expect(screen.getByText('#134')).toBeInTheDocument()
    expect(screen.getByText(/car/)).toBeInTheDocument()
    expect(screen.getByText('t=9.5s')).toBeInTheDocument()
    expect(screen.getByText('crosswalk_tripwire')).toBeInTheDocument()
  })

  it('calls onSelect when the row is clicked', () => {
    const onSelect = vi.fn()
    render(<IncidentCard event={mockEvent} onSelect={onSelect} />)

    const row = screen.getByText('t=9.5s').closest('[role="button"]')
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

  it('shows a real km/h figure only when the event actually carries a speed in its metadata', () => {
    const { rerender } = render(<IncidentCard event={mockEvent} />)
    expect(screen.queryByText(/km\/h/)).not.toBeInTheDocument()

    rerender(<IncidentCard event={{ ...mockEvent, metadata: { speed: 42.4 } }} />)
    expect(screen.getByText('42 km/h')).toBeInTheDocument()
  })
})
