import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Header } from './Header'
import type { Camera } from '@/lib/api'

const cameras: Camera[] = [
  { id: 1, camera_id: 'demo', name: null, location: null, calibration_reference: null },
  { id: 2, camera_id: 'demo-trafficlight', name: null, location: null, calibration_reference: null },
]

describe('Header', () => {
  it('shows system operational/offline based on isApiConnected, never a fabricated FPS/latency figure', () => {
    const { rerender } = render(
      <Header cameras={cameras} selectedCameraId="demo" onSelectCamera={vi.fn()} isApiConnected={true} />,
    )
    expect(screen.getByText('Operational')).toBeInTheDocument()
    expect(screen.queryByText(/FPS/)).not.toBeInTheDocument()
    expect(screen.queryByText(/LATENCY/)).not.toBeInTheDocument()

    rerender(<Header cameras={cameras} selectedCameraId="demo" onSelectCamera={vi.fn()} isApiConnected={false} />)
    expect(screen.getByText('Offline')).toBeInTheDocument()
  })

  it('shows the real feeds count as plain inline telemetry', () => {
    render(<Header cameras={cameras} selectedCameraId="demo" onSelectCamera={vi.fn()} />)
    expect(screen.getByText('Feeds:')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('does not show a targets reading when none was given (no camera/scene loaded)', () => {
    render(<Header cameras={cameras} selectedCameraId={null} onSelectCamera={vi.fn()} />)
    expect(screen.queryByText('Targets:')).not.toBeInTheDocument()
  })

  it('shows the real targets count when provided', () => {
    render(<Header cameras={cameras} selectedCameraId="demo-trafficlight" onSelectCamera={vi.fn()} targetsInFrame={130} />)
    expect(screen.getByText('Targets:')).toBeInTheDocument()
    expect(screen.getByText('130')).toBeInTheDocument()
  })

  it('hides the critical breach segment when there are no critical events', () => {
    render(
      <Header
        cameras={cameras}
        selectedCameraId="demo-trafficlight"
        onSelectCamera={vi.fn()}
        criticalEventCount={0}
        onSeekToCriticalEvent={vi.fn()}
      />,
    )
    expect(screen.queryByText(/Breach/)).not.toBeInTheDocument()
  })

  it('shows the critical breach segment and seeks to it on click', () => {
    const onSeek = vi.fn()
    render(
      <Header
        cameras={cameras}
        selectedCameraId="demo-trafficlight"
        onSelectCamera={vi.fn()}
        criticalEventCount={1}
        onSeekToCriticalEvent={onSeek}
      />,
    )

    fireEvent.click(screen.getByText('1 Breach'))
    expect(onSeek).toHaveBeenCalledTimes(1)
  })

  it('pluralizes the breach segment for more than one critical event', () => {
    render(
      <Header
        cameras={cameras}
        selectedCameraId="demo-trafficlight"
        onSelectCamera={vi.fn()}
        criticalEventCount={2}
        onSeekToCriticalEvent={vi.fn()}
      />,
    )
    expect(screen.getByText('2 Breaches')).toBeInTheDocument()
  })
})
