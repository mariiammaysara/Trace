import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Header } from './Header'
import type { Camera } from '@/lib/api'

const cameras: Camera[] = [
  { id: 1, camera_id: 'demo', name: null, location: null, calibration_reference: null },
  { id: 2, camera_id: 'demo-trafficlight', name: null, location: null, calibration_reference: null },
]

describe('Header', () => {
  it('shows system online/offline based on isApiConnected, never a fabricated FPS/latency figure', () => {
    const { rerender } = render(
      <Header cameras={cameras} selectedCameraId="demo" onSelectCamera={vi.fn()} isApiConnected={true} />,
    )
    expect(screen.getByText('SYSTEM ONLINE')).toBeInTheDocument()
    expect(screen.queryByText(/FPS/)).not.toBeInTheDocument()
    expect(screen.queryByText(/LATENCY/)).not.toBeInTheDocument()

    rerender(<Header cameras={cameras} selectedCameraId="demo" onSelectCamera={vi.fn()} isApiConnected={false} />)
    expect(screen.getByText('SYSTEM OFFLINE')).toBeInTheDocument()
  })

  it('does not show a targets-in-frame reading when none was given (no camera/scene loaded)', () => {
    render(<Header cameras={cameras} selectedCameraId={null} onSelectCamera={vi.fn()} />)
    expect(screen.queryByText(/TARGET/)).not.toBeInTheDocument()
  })

  it('shows the real targets-in-frame count when provided', () => {
    render(<Header cameras={cameras} selectedCameraId="demo-trafficlight" onSelectCamera={vi.fn()} targetsInFrame={130} />)
    expect(screen.getByText('130 TARGETS IN FRAME')).toBeInTheDocument()
  })

  it('hides the critical breach chip when there are no critical events', () => {
    render(
      <Header
        cameras={cameras}
        selectedCameraId="demo-trafficlight"
        onSelectCamera={vi.fn()}
        criticalEventCount={0}
        onSeekToCriticalEvent={vi.fn()}
      />,
    )
    expect(screen.queryByText(/CRITICAL BREACH/)).not.toBeInTheDocument()
  })

  it('shows the critical breach chip and seeks to it on click', () => {
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

    const chip = screen.getByText('1 CRITICAL BREACH')
    fireEvent.click(chip)
    expect(onSeek).toHaveBeenCalledTimes(1)
  })

  it('lets the feeds badge navigate to Cameras when wired, and renders as non-interactive otherwise', () => {
    const onNavigate = vi.fn()
    const { rerender } = render(
      <Header cameras={cameras} selectedCameraId="demo" onSelectCamera={vi.fn()} onNavigateToCameras={onNavigate} />,
    )
    fireEvent.click(screen.getByText('2 FEEDS CONNECTED'))
    expect(onNavigate).toHaveBeenCalledTimes(1)

    rerender(<Header cameras={cameras} selectedCameraId="demo" onSelectCamera={vi.fn()} />)
    expect(screen.getByText('2 FEEDS CONNECTED').closest('[role="button"]')).toBeNull()
  })
})
