/**
 * Phase 18: a stable, human-referenceable incident identifier, purely a
 * display format derived from the existing real `TraceEvent.id` -- no new
 * ID scheme in the database. `INC-###` is 1:1 with the event's real
 * database primary key, just formatted for someone to say/write down
 * ("investigating INC-014") instead of a bare integer.
 */
export function formatIncidentId(eventId: number): string {
  return `INC-${String(eventId).padStart(3, '0')}`
}
