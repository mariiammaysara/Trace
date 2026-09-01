import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EventBadge } from './EventBadge'

describe('EventBadge', () => {
  it('renders a violation event in --color-danger, not a brand or default color', () => {
    render(<EventBadge eventType="ZONE_ENTERED" />)
    const badge = screen.getByText('ZONE_ENTERED')
    expect(badge).toHaveClass('text-danger')
    expect(badge).not.toHaveClass('text-warning')
    expect(badge).not.toHaveClass('text-info')
  })

  it('renders a lifecycle event in --color-info', () => {
    render(<EventBadge eventType="OBJECT_APPEARED" />)
    const badge = screen.getByText('OBJECT_APPEARED')
    expect(badge).toHaveClass('text-info')
    expect(badge).not.toHaveClass('text-danger')
  })

  it('renders a notable-but-lesser event in --color-warning', () => {
    render(<EventBadge eventType="LOITERING" />)
    const badge = screen.getByText('LOITERING')
    expect(badge).toHaveClass('text-warning')
    expect(badge).not.toHaveClass('text-danger')
    expect(badge).not.toHaveClass('text-info')
  })
})
