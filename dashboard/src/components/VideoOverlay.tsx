import { useEffect, useRef, useState } from 'react'
import type { RefObject } from 'react'
import type { Line, TraceEvent, Trajectory, Zone } from '@/lib/api'
import { computePixelSpeed, findNearestPoint, getObjectViolationState } from '@/lib/overlay'
import type { ViolationState } from '@/lib/overlay'
import { cn } from '@/lib/utils'

interface VideoOverlayProps {
  videoRef: RefObject<HTMLVideoElement | null>
  videoWidth: number
  videoHeight: number
  trajectories: Trajectory[]
  events: TraceEvent[]
  zones: Zone[]
  lines: Line[]
  /** Phase 19: clicking a tracked object's box/label opens its Object
   * Profile -- the "video overlay" entry point Section 0's "clicking an
   * object_id anywhere" requires. */
  onSelectObject?: (objectId: number) => void
}

/** stroke/fill classes per violation state -- brand accent for normal
 * tracking, the two reserved semantic colors for an active event. Never a
 * hardcoded hex: these are Tailwind utilities resolving through the same
 * --color-* tokens as the rest of the dashboard. */
const STATE_CLASSES: Record<ViolationState, string> = {
  normal: 'stroke-accent fill-accent/10',
  warning: 'stroke-warning fill-warning/15',
  danger: 'stroke-danger fill-danger/15',
}

/** Soft outer glow per state, keyed to the same token the stroke already
 * uses -- referencing the CSS variable (not a literal hex) so this stays a
 * theme value, not a hardcoded color. */
const STATE_GLOW: Record<ViolationState, string> = {
  normal: 'drop-shadow-[0_0_3px_var(--color-accent)]',
  warning: 'drop-shadow-[0_0_3px_var(--color-warning)]',
  danger: 'drop-shadow-[0_0_4px_var(--color-danger)]',
}

/** Tag chip border (on the background rect) and text color (on the label
 * itself) per state -- same semantic mapping as STATE_CLASSES, just split
 * since the rect and the text need different fill/stroke roles. */
const STATE_LABEL_BORDER: Record<ViolationState, string> = {
  normal: 'stroke-accent/40',
  warning: 'stroke-warning/40',
  danger: 'stroke-danger/40',
}
const STATE_LABEL_TEXT: Record<ViolationState, string> = {
  normal: 'fill-accent',
  warning: 'fill-warning',
  danger: 'fill-danger',
}

const TRAIL_WINDOW_SECONDS = 3

/**
 * SVG overlay absolutely positioned over the <video>, synced to its
 * currentTime via requestAnimationFrame -- not baked into the video file,
 * not a CSS animation guessing at timing. viewBox matches the video's own
 * pixel dimensions so detection coordinates (already in that space) need no
 * manual scaling; the SVG element itself is sized to 100% and scales with
 * the video via CSS.
 */
export function VideoOverlay({
  videoRef,
  videoWidth,
  videoHeight,
  trajectories,
  events,
  zones,
  lines,
  onSelectObject,
}: VideoOverlayProps) {
  const [currentTime, setCurrentTime] = useState(0)
  const frameRef = useRef<number>(0)

  useEffect(() => {
    const tick = () => {
      const video = videoRef.current
      if (video) setCurrentTime(video.currentTime)
      frameRef.current = requestAnimationFrame(tick)
    }
    frameRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameRef.current)
  }, [videoRef])

  if (videoWidth === 0 || videoHeight === 0) return null

  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox={`0 0 ${videoWidth} ${videoHeight}`}
      preserveAspectRatio="xMidYMid meet"
      aria-hidden="true"
    >
      {zones.map((zone) => (
        <polygon
          key={`zone-${zone.id}`}
          points={zone.polygon.map(([x, y]) => `${x},${y}`).join(' ')}
          className="fill-accent/10 stroke-accent"
          strokeWidth={2}
          strokeDasharray="6 4"
        />
      ))}

      {lines.map((line) => (
        <line
          key={`line-${line.id}`}
          x1={line.start[0]}
          y1={line.start[1]}
          x2={line.end[0]}
          y2={line.end[1]}
          className="stroke-accent drop-shadow-[0_0_3px_var(--color-accent)]"
          strokeWidth={3}
        />
      ))}

      {trajectories.map((trajectory) => {
        const state = getObjectViolationState(trajectory.object_id, events, currentTime)
        const nearest = findNearestPoint(trajectory.points, currentTime)
        const trail = trajectory.points.filter(
          (point) => point.timestamp <= currentTime && currentTime - point.timestamp <= TRAIL_WINDOW_SECONDS,
        )
        // Real, already-available pixel-space speed (px/s) from the delta
        // between this object's two most recent trajectory points -- see
        // computePixelSpeed's own comment for why this stays pixel space
        // rather than claiming a real-world m/s or km/h figure.
        const pixelSpeed = computePixelSpeed(trajectory.points, currentTime)

        return (
          <g
            key={trajectory.object_id}
            className={cn(
              STATE_CLASSES[state],
              STATE_GLOW[state],
              'transition-colors duration-200 ease-out',
              onSelectObject && 'pointer-events-auto cursor-pointer',
            )}
            role={onSelectObject ? 'button' : undefined}
            tabIndex={onSelectObject ? 0 : undefined}
            aria-label={onSelectObject ? `Open object #${trajectory.object_id}'s profile` : undefined}
            onClick={onSelectObject ? () => onSelectObject(trajectory.object_id) : undefined}
            onKeyDown={
              onSelectObject
                ? (event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      onSelectObject(trajectory.object_id)
                    }
                  }
                : undefined
            }
          >
            {/* Trajectory tail as individually-faded segments (newest near
                full opacity, oldest fading toward the trail window's edge)
                rather than one flat-opacity polyline. */}
            {trail.length > 1 &&
              trail.slice(1).map((point, i) => {
                const previous = trail[i]
                const age = currentTime - point.timestamp
                const opacity = Math.max(0.08, 0.6 * (1 - age / TRAIL_WINDOW_SECONDS))
                return (
                  <line
                    key={`trail-${trajectory.object_id}-${point.frame_id}`}
                    x1={previous.x}
                    y1={previous.y}
                    x2={point.x}
                    y2={point.y}
                    strokeWidth={2}
                    opacity={opacity}
                  />
                )
              })}

            {nearest && (
              <>
                {nearest.x_min !== null && nearest.y_min !== null && nearest.x_max !== null && nearest.y_max !== null ? (
                  <rect
                    x={nearest.x_min}
                    y={nearest.y_min}
                    width={nearest.x_max - nearest.x_min}
                    height={nearest.y_max - nearest.y_min}
                    strokeWidth={1.5}
                  />
                ) : (
                  <circle cx={nearest.x} cy={nearest.y} r={6} strokeWidth={1.5} />
                )}
                {(() => {
                  const labelX = nearest.x_min ?? nearest.x
                  const labelY = (nearest.y_min ?? nearest.y) - 8
                  const label = [
                    `#${trajectory.object_id} ${trajectory.class_name}`,
                    pixelSpeed !== null ? `${Math.round(pixelSpeed)}px/s` : null,
                  ]
                    .filter(Boolean)
                    .join(' • ')
                  const labelWidth = label.length * 6.5 + 10
                  return (
                    <>
                      <rect
                        x={labelX}
                        y={labelY - 13}
                        width={labelWidth}
                        height={17}
                        rx={3}
                        className={cn('fill-primary/85', STATE_LABEL_BORDER[state])}
                        strokeWidth={1}
                      />
                      <text
                        x={labelX + 5}
                        y={labelY - 1}
                        fontSize={11}
                        className={cn('stroke-none font-medium font-mono tabular-nums', STATE_LABEL_TEXT[state])}
                      >
                        {label}
                      </text>
                    </>
                  )
                })()}
              </>
            )}
          </g>
        )
      })}
    </svg>
  )
}
