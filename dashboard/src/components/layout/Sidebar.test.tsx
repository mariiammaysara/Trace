import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Sidebar } from './Sidebar'

describe('Sidebar', () => {
  it('renders all three operational groups with their nav items', () => {
    render(<Sidebar activeView="dashboard" onNavigate={vi.fn()} />)

    expect(screen.getByText('Real-Time Surveillance')).toBeInTheDocument()
    expect(screen.getByText('Forensic Intelligence')).toBeInTheDocument()
    expect(screen.getByText('Analytics & Engine')).toBeInTheDocument()

    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Live Monitoring')).toBeInTheDocument()
    expect(screen.getByText('Camera Fleet')).toBeInTheDocument()
    expect(screen.getByText('Incidents & Events')).toBeInTheDocument()
    expect(screen.getByText('Investigation')).toBeInTheDocument()
    expect(screen.getByText('Vision Agent')).toBeInTheDocument()
    expect(screen.getByText('Alert Dispatch')).toBeInTheDocument()
    expect(screen.getByText('Traffic Analytics')).toBeInTheDocument()
    expect(screen.getByText('Model Evaluation')).toBeInTheDocument()
  })

  it('navigates when a nav item is clicked', () => {
    const onNavigate = vi.fn()
    render(<Sidebar activeView="dashboard" onNavigate={onNavigate} />)

    fireEvent.click(screen.getByText('Live Monitoring'))
    expect(onNavigate).toHaveBeenCalledWith('live')
  })

  it('shows the real live-feed count badge only when there is at least one camera', () => {
    const { rerender } = render(<Sidebar activeView="dashboard" onNavigate={vi.fn()} cameraCount={0} />)
    expect(screen.queryByText(/LIVE/)).not.toBeInTheDocument()

    rerender(<Sidebar activeView="dashboard" onNavigate={vi.fn()} cameraCount={3} />)
    expect(screen.getByText('3 LIVE')).toBeInTheDocument()
  })

  it('shows the real critical-breach badge only when there is at least one critical event', () => {
    const { rerender } = render(<Sidebar activeView="dashboard" onNavigate={vi.fn()} criticalEventCount={0} />)
    expect(screen.queryByText(/BREACH/)).not.toBeInTheDocument()

    rerender(<Sidebar activeView="dashboard" onNavigate={vi.fn()} criticalEventCount={1} />)
    expect(screen.getByText('1 BREACH')).toBeInTheDocument()

    rerender(<Sidebar activeView="dashboard" onNavigate={vi.fn()} criticalEventCount={2} />)
    expect(screen.getByText('2 BREACHES')).toBeInTheDocument()
  })

  it('never shows a pending-actions count, FPS/CPU reading, or a version tag -- none of these are backed by a real endpoint', () => {
    render(<Sidebar activeView="dashboard" onNavigate={vi.fn()} />)

    expect(screen.queryByText(/PENDING/)).not.toBeInTheDocument()
    expect(screen.queryByText(/FPS/)).not.toBeInTheDocument()
    expect(screen.queryByText(/CPU/)).not.toBeInTheDocument()
    expect(screen.queryByText(/^v\d/)).not.toBeInTheDocument()
  })

  it('reflects the real system connectivity and feed count in the footer', () => {
    const { rerender } = render(<Sidebar activeView="dashboard" onNavigate={vi.fn()} isApiConnected={true} cameraCount={3} />)
    expect(screen.getByText('Operational')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('PostgreSQL 16')).toBeInTheDocument()

    rerender(<Sidebar activeView="dashboard" onNavigate={vi.fn()} isApiConnected={false} />)
    expect(screen.getByText('Offline')).toBeInTheDocument()
  })

  describe('collapsed rail mode', () => {
    it('hides labels and group headers, but keeps every nav item clickable by icon alone', () => {
      const onNavigate = vi.fn()
      render(<Sidebar activeView="dashboard" onNavigate={onNavigate} cameraCount={3} criticalEventCount={1} />)

      fireEvent.click(screen.getByLabelText('Collapse sidebar'))

      expect(screen.queryByText('Real-Time Surveillance')).not.toBeInTheDocument()
      // The label only survives inside the (always-mounted, CSS-hidden until
      // hover) tooltip -- exactly one instance, not a second visible copy.
      expect(screen.getAllByText('Live Monitoring')).toHaveLength(1)
      expect(screen.getByText('3 LIVE')).toBeInTheDocument()
      expect(screen.getByText('1 BREACH')).toBeInTheDocument()

      fireEvent.click(screen.getByRole('button', { name: 'Live Monitoring' }))
      expect(onNavigate).toHaveBeenCalledWith('live')
    })

    it('expands again from the rail via the same toggle', () => {
      render(<Sidebar activeView="dashboard" onNavigate={vi.fn()} />)

      fireEvent.click(screen.getByLabelText('Collapse sidebar'))
      expect(screen.getAllByText('Overview')).toHaveLength(1)

      fireEvent.click(screen.getByLabelText('Expand sidebar'))
      expect(screen.getByText('Overview')).toBeInTheDocument()
    })
  })
})
