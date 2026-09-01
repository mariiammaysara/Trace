import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BarChart, type BarChartDatum } from './BarChart'

describe('BarChart', () => {
  it('renders a danger-variant bar with the danger color, not accent', () => {
    const data: BarChartDatum[] = [
      { key: 'OBJECT_APPEARED', label: 'OBJECT_APPEARED', value: 4, variant: 'accent' },
      { key: 'ZONE_ENTERED', label: 'ZONE_ENTERED', value: 2, variant: 'danger' },
    ]
    render(<BarChart data={data} />)

    const dangerBar = screen.getByTestId('bar-ZONE_ENTERED')
    expect(dangerBar).toHaveClass('bg-danger')
    expect(dangerBar).not.toHaveClass('bg-accent')

    const normalBar = screen.getByTestId('bar-OBJECT_APPEARED')
    expect(normalBar).toHaveClass('bg-accent')
    expect(normalBar).not.toHaveClass('bg-danger')
  })

  it('renders a warning-variant bar with the warning color', () => {
    const data: BarChartDatum[] = [{ key: 'LOITERING', label: 'LOITERING', value: 1, variant: 'warning' }]
    render(<BarChart data={data} />)

    expect(screen.getByTestId('bar-LOITERING')).toHaveClass('bg-warning')
  })

  it('defaults to accent when no variant is given', () => {
    const data: BarChartDatum[] = [{ key: 'person', label: 'person', value: 3 }]
    render(<BarChart data={data} />)

    expect(screen.getByTestId('bar-person')).toHaveClass('bg-accent')
  })

  it('shows the empty message when every value is zero', () => {
    render(<BarChart data={[{ key: 'a', label: 'a', value: 0 }]} emptyMessage="Nothing here yet." />)
    expect(screen.getByText('Nothing here yet.')).toBeInTheDocument()
  })

  it('renders vertical orientation bars with their variant color too', () => {
    const data: BarChartDatum[] = [
      { key: '0', label: '00', value: 5, variant: 'accent' },
      { key: '3', label: '03', value: 9, variant: 'danger' },
    ]
    render(<BarChart data={data} orientation="vertical" />)

    expect(screen.getByTestId('bar-3')).toHaveClass('bg-danger')
    expect(screen.getByTestId('bar-0')).toHaveClass('bg-accent')
  })
})
