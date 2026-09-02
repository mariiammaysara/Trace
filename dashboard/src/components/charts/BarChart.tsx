import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import type { ChartVariant } from '@/lib/eventClassification'

export interface BarChartDatum {
  key: string
  label: string
  value: number
  variant?: ChartVariant | 'secondary'
  title?: string
}

const VARIANT_BG: Record<string, string> = {
  accent: 'bg-accent',
  secondary: 'bg-secondary',
  warning: 'bg-warning',
  danger: 'bg-danger',
}

interface BarChartProps {
  data: BarChartDatum[]
  orientation?: 'horizontal' | 'vertical'
  emptyMessage?: string
  className?: string
}

/**
 * A small, dependency-free bar chart. Each bar animates in from zero once
 * -- on mount, and again whenever `data` changes reference (a fresh fetch)
 * -- then holds still. There is no looping/continuous motion on static
 * data, per the design system's chart-animation rule (DESIGN_SYSTEM.md).
 */
export function BarChart({ data, orientation = 'horizontal', emptyMessage, className }: BarChartProps) {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    setReady(false)
    const raf = requestAnimationFrame(() => setReady(true))
    return () => cancelAnimationFrame(raf)
  }, [data])

  const realMax = Math.max(0, ...data.map((d) => d.value))

  if (data.length === 0 || realMax === 0) {
    return <p className="text-sm text-ink-subtle">{emptyMessage ?? 'No data yet.'}</p>
  }

  const max = realMax

  if (orientation === 'vertical') {
    return (
      <div className={cn('flex h-28 items-end gap-1', className)}>
        {data.map((datum, index) => {
          const pct = (datum.value / max) * 100
          return (
            <div key={datum.key} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
              <div
                title={datum.title ?? `${datum.label}: ${datum.value}`}
                data-testid={`bar-${datum.key}`}
                data-variant={datum.variant ?? 'accent'}
                className={cn(
                  'w-full min-h-[2px] rounded-t transition-[height] duration-500 ease-out',
                  VARIANT_BG[datum.variant ?? 'accent'],
                )}
                style={{
                  height: ready ? `${Math.max(pct, datum.value > 0 ? 4 : 0)}%` : '0%',
                  transitionDelay: `${Math.min(index * 15, 300)}ms`,
                }}
              />
              <span className="font-mono text-[10px] text-ink-subtle">{index % 3 === 0 ? datum.label : ''}</span>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {data.map((datum, index) => {
        const pct = (datum.value / max) * 100
        return (
          <div key={datum.key} className="flex items-center gap-3">
            <span className="w-32 shrink-0 truncate text-sm text-ink-subtle" title={datum.label}>
              {datum.label}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-alt">
              <div
                data-testid={`bar-${datum.key}`}
                data-variant={datum.variant ?? 'accent'}
                className={cn('h-full rounded-full transition-[width] duration-500 ease-out', VARIANT_BG[datum.variant ?? 'accent'])}
                style={{
                  width: ready ? `${Math.max(pct, datum.value > 0 ? 2 : 0)}%` : '0%',
                  transitionDelay: `${Math.min(index * 40, 400)}ms`,
                }}
              />
            </div>
            <span className="w-10 shrink-0 text-right font-mono text-sm tabular-nums text-ink">{datum.value}</span>
          </div>
        )
      })}
    </div>
  )
}
