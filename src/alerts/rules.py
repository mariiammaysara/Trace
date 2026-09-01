"""Which real-time events trigger an automatic alert (Section 13). Kept as
a plain, pure, extensible rule -- no LLM, no agent, no DB access here -- so
`database.repository.add_event_from_pipeline` can call it synchronously for
every persisted event without adding any nondeterminism or side-channel
dependency to the write path, matching Section 7's event engine being
deterministic/rule-based.

OVERSPEED is the one enabled by default, per this phase's explicit
requirement; "or other configured" just means extending this set --
STOPPED/LOITERING are commented candidates, not enabled, since they're
already the WARNING-severity tier elsewhere in this codebase (Section 7's
event types, the dashboard's src/lib/eventSeverity.ts) and enabling them
here is a product decision for a later phase, not implied by this one.
"""

ALERT_TRIGGERING_EVENT_TYPES = {"OVERSPEED"}


def should_alert(event_type: str) -> bool:
    return event_type in ALERT_TRIGGERING_EVENT_TYPES
