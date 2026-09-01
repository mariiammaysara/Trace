import { useEffect, useRef, useState } from 'react'
import type { RefObject } from 'react'
import type { Line, TraceEvent, Trajectory, Zone } from '@/lib/api'
import { findNearestPoint, getObjectViolationState } from '@/lib/overlay'
import type { ViolationState } from '@/lib/overlay'

interface VideoOverlayProps {
  videoRef: RefObject<HTMLVideoElement | null>
  videoWidth: number
  videoHeight: number
  trajectories: Trajectory[]
  events: TraceEvent[]
  zones: Zone[]
  lines: Line[]
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
          className="stroke-accent"
          strokeWidth={3}
        />
      ))}

      {trajectories.map((trajectory) => {
        const state = getObjectViolationState(trajectory.object_id, events, currentTime)
        const nearest = findNearestPoint(trajectory.points, currentTime)
        const trail = trajectory.points.filter(
          (point) => point.timestamp <= currentTime && currentTime - point.timestamp <= TRAIL_WINDOW_SECONDS,
        )

        return (
          <g key={trajectory.object_id} className={`${STATE_CLASSES[state]} transition-colors duration-200 ease-out`}>
            {trail.length > 1 && (
              <polyline
                points={trail.map((point) => `${point.x},${point.y}`).join(' ')}
                fill="none"
                strokeWidth={2}
                opacity={0.6}
              />
            )}

            {nearest && (
              <>
                {nearest.x_min !== null && nearest.y_min !== null && nearest.x_max !== null && nearest.y_max !== null ? (
                  <rect
                    x={nearest.x_min}
                    y={nearest.y_min}
                    width={nearest.x_max - nearest.x_min}
                    height={nearest.y_max - nearest.y_min}
                    strokeWidth={2}
                  />
                ) : (
                  <circle cx={nearest.x} cy={nearest.y} r={6} strokeWidth={2} />
                )}
                <text
                  x={nearest.x_min ?? nearest.x}
                  y={(nearest.y_min ?? nearest.y) - 6}
                  fontSize={14}
                  className="fill-current stroke-none font-medium"
                >
                  #{trajectory.object_id} {trajectory.class_name}
                </text>
              </>
            )}
          </g>
        )
      })}
    </svg>
  )
}
