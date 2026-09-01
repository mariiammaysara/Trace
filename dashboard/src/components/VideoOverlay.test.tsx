import { render, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { RefObject } from 'react'
import { VideoOverlay } from './VideoOverlay'
import type { TraceEvent, Trajectory } from '@/lib/api'

/**
 * VideoOverlay only ever reads .current.currentTime from the ref -- a plain
 * object satisfying that is enough, and sidesteps jsdom's incomplete
 * HTMLVideoElement implementation entirely.
 */
function fakeVideoRef(currentTime: number): RefObject<HTMLVideoElement | null> {
  return { current: { currentTime } as HTMLVideoElement }
}

function makeTrajectory(objectId: number): Trajectory {
  return {
    object_id: objectId,
    camera_id: 'demo',
    class_name: 'person',
    first_seen: 0,
    last_seen: 10,
    points: [{ frame_id: 0, timestamp: 5.0, x: 100, y: 100, x_min: 80, y_min: 80, x_max: 120, y_max: 120 }],
  }
}

function makeEvent(overrides: Partial<TraceEvent>): TraceEvent {
  return {
    id: 1,
    object_id: 1,
    event_type: 'OBJECT_APPEARED',
    class_name: 'person',
    timestamp: 5.0,
    confidence: 0.9,
    metadata: {},
    zone_id: null,
    line_id: null,
    ...overrides,
  }
}

describe('VideoOverlay', () => {
  it('renders an object with no active event using the brand accent color, not danger', async () => {
    const { container } = render(
      <VideoOverlay
        videoRef={fakeVideoRef(5.0)}
        videoWidth={640}
        videoHeight={480}
        trajectories={[makeTrajectory(1)]}
        events={[]}
        zones={[]}
        lines={[]}
      />,
    )

    await waitFor(() => expect(container.querySelector('rect')).not.toBeNull())

    const group = container.querySelector('g')
    expect(group).toHaveClass('stroke-accent')
    expect(group).not.toHaveClass('stroke-danger')
  })

  it('renders an object mid-line-crossing with --color-danger, not a brand/default color', async () => {
    const events = [makeEvent({ object_id: 1, event_type: 'LINE_CROSSED', timestamp: 5.0 })]

    const { container } = render(
      <VideoOverlay
        videoRef={fakeVideoRef(5.0)}
        videoWidth={640}
        videoHeight={480}
        trajectories={[makeTrajectory(1)]}
        events={events}
        zones={[]}
        lines={[]}
      />,
    )

    await waitFor(() => expect(container.querySelector('rect')).not.toBeNull())

    const group = container.querySelector('g')
    expect(group).toHaveClass('stroke-danger')
    expect(group).not.toHaveClass('stroke-accent')
  })

  it('renders an object inside a zone with --color-danger for the whole time it is inside', async () => {
    const events = [
      makeEvent({ object_id: 1, event_type: 'ZONE_ENTERED', timestamp: 1.0, zone_id: 'restricted' }),
      makeEvent({ object_id: 1, event_type: 'ZONE_EXITED', timestamp: 9.0, zone_id: 'restricted' }),
    ]

    const { container } = render(
      <VideoOverlay
        videoRef={fakeVideoRef(5.0)}
        videoWidth={640}
        videoHeight={480}
        trajectories={[makeTrajectory(1)]}
        events={events}
        zones={[]}
        lines={[]}
      />,
    )

    await waitFor(() => expect(container.querySelector('rect')).not.toBeNull())

    expect(container.querySelector('g')).toHaveClass('stroke-danger')
  })

  it('does not render an svg at all before video dimensions are known', () => {
    const { container } = render(
      <VideoOverlay
        videoRef={fakeVideoRef(0)}
        videoWidth={0}
        videoHeight={0}
        trajectories={[]}
        events={[]}
        zones={[]}
        lines={[]}
      />,
    )
    expect(container.querySelector('svg')).toBeNull()
  })
})
