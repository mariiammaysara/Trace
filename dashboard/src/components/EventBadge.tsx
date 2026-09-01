import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { classifyEventSeverity } from '@/lib/eventSeverity'

const SEVERITY_CLASSES: Record<string, string> = {
  danger: 'border-danger/30 bg-danger/10 text-danger',
  warning: 'border-warning/30 bg-warning/10 text-warning',
  info: 'border-info/30 bg-info/10 text-info',
}

/**
 * An event-type badge colored per DESIGN_SYSTEM.md's documented
 * event->severity mapping (src/lib/eventSeverity.ts) -- always one of
 * TRACE's semantic states, never a brand color, since a badge is one of
 * tokens.css's explicitly-reserved semantic-color surfaces.
 */
export function EventBadge({ eventType }: { eventType: string }) {
  const severity = classifyEventSeverity(eventType)
  return (
    <Badge
      variant="outline"
      data-severity={severity}
      className={cn('font-medium tabular-nums', SEVERITY_CLASSES[severity])}
    >
      {eventType}
    </Badge>
  )
}
