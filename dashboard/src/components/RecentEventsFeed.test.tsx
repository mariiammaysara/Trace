import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RecentEventsFeed } from './RecentEventsFeed'
import type { TraceEvent } from '@/lib/api'

function makeEvent(id: number, eventType: string): TraceEvent {
  return {
    id,
    object_id: 1,
    event_type: eventType,
    class_name: 'person',
    timestamp: id,
    confidence: 0.9,
    metadata: {},
    zone_id: null,
    line_id: null,
  }
}

describe('RecentEventsFeed', () => {
  // Item 5: a long, mostly-lifecycle-noise event list (OBJECT_APPEARED/
  // DISAPPEARED) used to bury the real violations and warnings in
  // chronological order. The default "All" view now groups by severity
  // (reusing eventSeverity.ts's own danger/warning/info tiers) so danger and
  // warning events always render above info-tier noise, without hiding or
  // discarding anything.
  it('sorts danger and warning events above info-tier lifecycle noise, preserving order within each tier', () => {
    const events: TraceEvent[] = [
      makeEvent(1, 'OBJECT_APPEARED'),
      makeEvent(2, 'OBJECT_DISAPPEARED'),
      makeEvent(3, 'OVERSPEED'),
      makeEvent(4, 'OBJECT_APPEARED'),
      makeEvent(5, 'LOITERING'),
      makeEvent(6, 'LINE_CROSSED'),
    ]

    const { container } = render(<RecentEventsFeed events={events} />)

    // Each row's event type renders as its own severity-colored span
    // (IncidentCard) -- read them back in DOM order.
    const eventTypesInOrder = Array.from(container.querySelectorAll('[role="button"]')).map(
      (row) => row.querySelector('span.font-semibold')?.textContent,
    )

    // danger (OVERSPEED, LINE_CROSSED) first, then warning (LOITERING), then
    // info (OBJECT_APPEARED x2, OBJECT_DISAPPEARED) -- original relative
    // order preserved inside each tier.
    expect(eventTypesInOrder).toEqual(['OVERSPEED', 'LINE_CROSSED', 'LOITERING', 'OBJECT_APPEARED', 'OBJECT_DISAPPEARED', 'OBJECT_APPEARED'])
  })

  it('still shows only one severity tier when a quick filter is active', () => {
    const events: TraceEvent[] = [
      makeEvent(1, 'OBJECT_APPEARED'),
      makeEvent(2, 'OVERSPEED'),
      makeEvent(3, 'LOITERING'),
    ]

    render(<RecentEventsFeed events={events} />)

    fireEvent.click(screen.getByRole('button', { name: /Violations \(1\)/ }))

    expect(screen.getByText('OVERSPEED')).toBeInTheDocument()
    expect(screen.queryByText('OBJECT_APPEARED')).not.toBeInTheDocument()
    expect(screen.queryByText('LOITERING')).not.toBeInTheDocument()
  })
})
