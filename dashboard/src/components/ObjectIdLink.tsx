import type { MouseEvent } from 'react'
import { cn } from '@/lib/utils'

interface ObjectIdLinkProps {
  objectId: number
  onSelectObject?: (objectId: number) => void
  className?: string
}

/**
 * Phase 19: the one clickable rendering of `#{object_id}` reused everywhere
 * an object id appears (video overlay labels, event rows, the incident
 * view) so opening its Object Profile behaves identically no matter where
 * it's clicked from. Renders as plain (non-interactive) text when no
 * onSelectObject is wired for that context, so this is a drop-in
 * replacement for the old `#{event.object_id}` spans.
 */
export function ObjectIdLink({ objectId, onSelectObject, className }: ObjectIdLinkProps) {
  if (!onSelectObject) {
    return <span className={className}>#{objectId}</span>
  }

  function handleClick(event: MouseEvent) {
    event.stopPropagation()
    onSelectObject?.(objectId)
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn('rounded hover:text-accent hover:underline focus-visible:outline-2 focus-visible:outline-accent', className)}
      aria-label={`Open object #${objectId}'s profile`}
    >
      #{objectId}
    </button>
  )
}
