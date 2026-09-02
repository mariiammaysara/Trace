import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string
  /** 'danger' marks a stat that represents a violation-class metric (Section 11's
   * zone_violation_count framing) -- rendered in --color-danger, not brand blue. */
  variant?: 'default' | 'danger'
  hint?: string
}

/**
 * A compact operational KPI tile -- value dominates, label identifies it,
 * hint gives one line of context. Deliberately not built on the generic
 * shadcn Card (its default padding/radius/ring reads as admin-template
 * filler at this density): a plain bordered surface with a severity accent
 * on the left edge, matching the same left-border convention used for event
 * severity everywhere else in the app.
 */
export function StatCard({ label, value, variant = 'default', hint }: StatCardProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-0.5 rounded-md border border-border bg-surface px-3.5 py-3 border-l-[3px]',
        variant === 'danger' ? 'border-l-danger' : 'border-l-transparent',
      )}
    >
      <span className="text-[11px] font-semibold uppercase tracking-wide text-ink-quiet">
        {label}
      </span>
      <p
        data-testid={`stat-value-${label}`}
        className={cn(
          'font-mono text-[26px] font-semibold leading-none tabular-nums',
          variant === 'danger' ? 'text-danger' : 'text-ink',
        )}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-ink-subtle">{hint}</p>}
    </div>
  )
}
