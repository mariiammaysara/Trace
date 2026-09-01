import { describe, expect, it } from 'vitest'
import { DANGER_EVENT_TYPES as OVERLAY_DANGER, WARNING_EVENT_TYPES as OVERLAY_WARNING } from './overlay'
import { classifyEventType } from './eventClassification'
import { classifyEventSeverity, ALL_EVENT_TYPES } from './eventSeverity'

/**
 * Phase 10.3 required the badge mapping (eventSeverity.ts) to stay
 * consistent with Phase 10.1's Live overlay (overlay.ts) and Phase 10.2's
 * Analytics chart (eventClassification.ts) -- three separately-written
 * modules with no shared import, so nothing stops them drifting apart
 * silently. This test compares all three directly instead of trusting that
 * they were written consistently.
 *
 * ZONE_ENTERED/ZONE_EXITED are excluded from the direct per-type diff below:
 * overlay.ts doesn't put them in its static DANGER/WARNING sets because it
 * brackets them as a real "inside the zone" time interval instead (see
 * overlay.ts's getObjectViolationState) -- structurally different from a
 * flash, but the same danger-tier *effect* while the object is inside. That
 * behavior is already covered by overlay.test.ts; this file only asserts
 * the chart and badge mappings (which both use plain static sets) agree on
 * ZONE_ENTERED explicitly.
 */
describe('event color mapping stays consistent across the Live overlay, Analytics chart, and Events badge', () => {
  const typesWithDirectOverlayEquivalents = ALL_EVENT_TYPES.filter(
    (type) => type !== 'ZONE_ENTERED' && type !== 'ZONE_EXITED',
  )

  it.each(typesWithDirectOverlayEquivalents)('%s has the same danger/warning tier in the overlay, chart, and badge', (type) => {
    const overlayTier = OVERLAY_DANGER.has(type) ? 'danger' : OVERLAY_WARNING.has(type) ? 'warning' : 'normal'
    const chartTier = classifyEventType(type)
    const badgeTier = classifyEventSeverity(type)

    if (overlayTier === 'danger') {
      expect(chartTier).toBe('danger')
      expect(badgeTier).toBe('danger')
    } else if (overlayTier === 'warning') {
      expect(chartTier).toBe('warning')
      expect(badgeTier).toBe('warning')
    } else {
      // overlay's default bucket ('normal') and the chart's default bucket
      // ('accent') are the same brand-color tier by design; the badge's
      // default bucket ('info') is a different literal color on purpose
      // (badges reserve full semantic color, charts/overlays reserve it for
      // violations only) but must still be the *non-severe* tier, not
      // danger or warning.
      expect(chartTier).toBe('accent')
      expect(badgeTier).toBe('info')
    }
  })

  it('ZONE_ENTERED is danger-tier in both the chart and badge mappings (overlay brackets it separately -- see overlay.test.ts)', () => {
    expect(classifyEventType('ZONE_ENTERED')).toBe('danger')
    expect(classifyEventSeverity('ZONE_ENTERED')).toBe('danger')
  })

  it('ZONE_EXITED is non-severe in both the chart and badge mappings', () => {
    expect(classifyEventType('ZONE_EXITED')).toBe('accent')
    expect(classifyEventSeverity('ZONE_EXITED')).toBe('info')
  })
})
