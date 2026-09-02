import { useEffect, useState } from 'react'
import { listCameraAlerts } from '@/lib/api'
import type { AlertRecord, Camera } from '@/lib/api'
import { EventBadge } from '@/components/EventBadge'
import { ShieldAlert, ShieldCheck } from 'lucide-react'

interface AlertsViewProps {
  cameras: Camera[]
}

/**
 * Alert Dispatch: real delivered-alert records (GET
 * /cameras/{camera_id}/alerts, aggregated across every registered camera),
 * not a placeholder. An Alert row is created automatically
 * (src/database/repository.py's should_alert, src/alerts/rules.py) only for
 * OVERSPEED right now -- that's a real, current, deliberately narrow rule
 * (the module docstring: STOPPED/LOITERING are commented-out candidates,
 * not a product decision made yet), so this page says exactly that rather
 * than the old placeholder copy's broader "Overspeed, Zone Intrusion,
 * Sudden Stop" claim, which was never actually true.
 */
export function AlertsView({ cameras }: AlertsViewProps) {
  const [alerts, setAlerts] = useState<AlertRecord[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (cameras.length === 0) {
      setAlerts([])
      return
    }
    let cancelled = false
    setError(null)

    Promise.allSettled(cameras.map((camera) => listCameraAlerts(camera.camera_id)))
      .then((results) => {
        if (cancelled) return
        // Only treat this as "checked, zero alerts" if at least one camera's
        // request actually succeeded -- if every single one failed (stale
        // backend, network down), that's a real error, not an empty result,
        // and showing "No active alerts" for it would misrepresent a check
        // that never happened.
        const succeeded = results.filter((r) => r.status === 'fulfilled')
        if (succeeded.length === 0) {
          const firstFailure = results.find((r) => r.status === 'rejected') as PromiseRejectedResult | undefined
          throw firstFailure ? firstFailure.reason : new Error('failed to load alerts')
        }
        const merged = succeeded
          .flatMap((r) => (r as PromiseFulfilledResult<AlertRecord[]>).value)
          .sort((a, b) => b.created_at.localeCompare(a.created_at))
        setAlerts(merged)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(String(err))
      })

    return () => {
      cancelled = true
    }
  }, [cameras])

  return (
    <div className="flex flex-col gap-4 max-w-4xl">
      {error && (
        <div role="alert" className="rounded-md border border-danger bg-danger/10 px-4 py-2 text-sm text-danger">
          {error}
        </div>
      )}

      {/* Status strip */}
      <div className="flex flex-wrap items-center divide-x divide-border rounded-md border border-border bg-surface">
        <div className="flex items-center gap-1.5 px-3.5 py-2">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          <span className="text-xs font-medium text-ink">Alert dispatch active</span>
        </div>
        <div className="flex items-center gap-1.5 px-3.5 py-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Trigger rule</span>
          <EventBadge eventType="OVERSPEED" />
        </div>
        <div className="flex items-center gap-1.5 px-3.5 py-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">Deliveries</span>
          <span className="font-mono text-sm font-semibold text-ink">{alerts ? alerts.length : '—'}</span>
        </div>
      </div>

      {alerts === null ? (
        <p className="text-sm text-ink-subtle">Loading alerts…</p>
      ) : alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed border-border bg-surface-alt/30 py-10 text-center">
          <ShieldCheck className="h-6 w-6 text-ink-disabled" />
          <p className="text-sm font-semibold text-ink">No active alerts</p>
          <p className="max-w-sm text-xs text-ink-subtle">
            No OVERSPEED violations have triggered a dispatched alert yet for the registered cameras.
          </p>
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-surface divide-y divide-border overflow-hidden">
          {alerts.map((alert) => (
            <div key={alert.id} className="flex items-center gap-3 px-3.5 py-2.5">
              <ShieldAlert className="h-4 w-4 text-danger shrink-0" />
              <EventBadge eventType={alert.event_type} />
              <span className="flex-1 min-w-0 truncate text-sm text-ink">{alert.message}</span>
              <span className="font-mono text-[11px] text-ink-subtle shrink-0">{alert.camera_id}</span>
              <span className="rounded bg-surface-alt px-1.5 py-0.5 text-[10px] font-mono text-ink-subtle shrink-0">
                {alert.channel}
              </span>
              <span className="font-mono text-[11px] text-ink-subtle tabular-nums shrink-0 w-36 text-right">
                {new Date(alert.created_at).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs text-ink-subtle">
        Alerts are created automatically when a qualifying event is ingested (currently OVERSPEED only) and
        delivered to this dashboard. Additional trigger types and delivery channels are supported by the alert
        pipeline but not yet enabled.
      </p>
    </div>
  )
}
