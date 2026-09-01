import { Card, CardContent, CardHeader, CardDescription } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string
  /** 'danger' marks a stat that represents a violation-class metric (Section 11's
   * zone_violation_count framing) -- rendered in --color-danger, not brand blue. */
  variant?: 'default' | 'danger'
  hint?: string
}

export function StatCard({ label, value, variant = 'default', hint }: StatCardProps) {
  return (
    <Card className={variant === 'danger' ? 'ring-2 ring-danger/40' : undefined}>
      <CardHeader>
        <CardDescription className="text-xs font-medium uppercase tracking-wide text-secondary">
          {label}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p
          data-testid={`stat-value-${label}`}
          className={cn('text-2xl font-semibold tabular-nums', variant === 'danger' ? 'text-danger' : 'text-primary')}
        >
          {value}
        </p>
        {hint && <p className="mt-1 text-xs text-secondary">{hint}</p>}
      </CardContent>
    </Card>
  )
}
