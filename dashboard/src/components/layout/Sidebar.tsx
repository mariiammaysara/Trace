import {
  LayoutDashboard,
  Radio,
  Camera,
  ShieldAlert,
  SearchCheck,
  Bot,
  BellRing,
  BarChart3,
  Cpu,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export type ActiveView = 'dashboard' | 'live' | 'cameras' | 'events' | 'analytics' | 'investigations' | 'alerts' | 'agent' | 'evaluation'

interface NavItem {
  id: ActiveView
  label: string
  icon: typeof LayoutDashboard
  /** Static label badge, e.g. "AI COPILOT" -- always shown. */
  badge?: string
}

interface NavGroup {
  title: string
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Real-Time Surveillance',
    items: [
      { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
      { id: 'live', label: 'Live Monitoring', icon: Radio },
      { id: 'cameras', label: 'Camera Fleet', icon: Camera },
    ],
  },
  {
    title: 'Forensic Intelligence',
    items: [
      { id: 'events', label: 'Incidents & Events', icon: ShieldAlert },
      { id: 'investigations', label: 'Investigation', icon: SearchCheck },
      { id: 'agent', label: 'Vision Agent', icon: Bot, badge: 'AI COPILOT' },
      { id: 'alerts', label: 'Alert Dispatch', icon: BellRing },
    ],
  },
  {
    title: 'Analytics & Engine',
    items: [
      { id: 'analytics', label: 'Traffic Analytics', icon: BarChart3 },
      { id: 'evaluation', label: 'Model Evaluation', icon: Cpu },
    ],
  },
]

interface SidebarProps {
  activeView: ActiveView
  onNavigate: (view: ActiveView) => void
  cameraCount?: number
  isApiConnected?: boolean
  /** Real count of currently-active danger-severity events (reusing
   * eventSeverity.ts's classification, same source as the header's critical
   * breach chip) -- omitted/0 hides the badge entirely rather than showing
   * a fabricated "0 BREACH". */
  criticalEventCount?: number
}

const BADGE_BASE = 'flex items-center gap-1 rounded border text-[9px] font-mono px-1.5 py-0.5 shrink-0'

/**
 * Three operational groups (Real-Time Surveillance / Forensic Intelligence /
 * Analytics & Engine) instead of one flat list, plus a real system-status
 * footer. Every badge here is real, already-available data -- there is
 * deliberately no FPS/CPU reading or pending-action count in the footer/nav:
 * neither is computed or exposed anywhere the frontend can read yet (no
 * list/count endpoint exists for pending agent actions, and per-camera FPS
 * was already established as unavailable when the header's telemetry strip
 * was built -- see CamerasView.tsx's own note on that).
 */
export function Sidebar({ activeView, onNavigate, cameraCount = 0, isApiConnected = true, criticalEventCount = 0 }: SidebarProps) {
  return (
    <aside
      aria-label="Sidebar Navigation"
      className="flex h-screen w-64 shrink-0 flex-col border-r border-border bg-primary text-ink-on-dark select-none"
    >
      {/* Brand -- symbol from brand/symbol-color-on-dark.svg (public/trace-symbol.svg);
          wordmark stays live text rather than baked into the SVG so it renders in
          a real webfont instead of falling back to a system sans (an
          externally-loaded <img> SVG can't see the page's web fonts).
          Font is pinned inline to Geist Variable on purpose -- a separate,
          deliberate brand choice that must not follow --font-sans (Exo 2)
          when the general UI typeface changes. */}
      <div className="flex h-12 shrink-0 items-center gap-2 border-b border-border/20 px-3.5">
        <img src="/trace-symbol.svg" alt="" className="h-4 w-4 shrink-0" />
        <span
          className="text-sm font-semibold tracking-wide text-ink-on-dark leading-none"
          style={{ fontFamily: "'Geist Variable', sans-serif" }}
        >
          TRACE
        </span>
      </div>

      {/* Main Navigation */}
      <div className="flex flex-1 flex-col justify-between overflow-y-auto px-2 py-3">
        <nav className="flex flex-col gap-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="flex flex-col gap-1">
              <span className="px-3 mb-1 text-[10px] font-mono font-medium tracking-widest text-ink-on-dark-subtle uppercase">
                {group.title}
              </span>

              <div className="flex flex-col gap-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon
                  const isActive = activeView === item.id
                  const showLiveBadge = item.id === 'live' && cameraCount > 0
                  const showBreachBadge = item.id === 'events' && criticalEventCount > 0

                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => onNavigate(item.id)}
                      aria-current={isActive ? 'page' : undefined}
                      className={cn(
                        'group relative flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-xs font-medium transition-all',
                        'focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-1',
                        isActive
                          ? 'border-l-2 border-l-accent bg-accent/10 text-accent font-semibold shadow-[0_0_12px_var(--color-accent)]'
                          : 'border-l-2 border-l-transparent text-ink-on-dark-quiet hover:bg-surface/10 hover:text-ink-on-dark',
                      )}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <Icon
                          className={cn(
                            'h-3.5 w-3.5 shrink-0 transition-colors',
                            isActive ? 'text-accent' : 'text-accent/70 group-hover:text-ink-on-dark',
                          )}
                        />
                        <span className="truncate">{item.label}</span>
                      </div>

                      {item.badge && (
                        <span className={cn(BADGE_BASE, 'border-accent/40 bg-accent/10 text-accent')}>
                          {item.badge}
                        </span>
                      )}

                      {showLiveBadge && (
                        <span className={cn(BADGE_BASE, 'border-success/30 bg-success/10 text-success')}>
                          <span className="relative flex h-1.5 w-1.5">
                            <span className="motion-safe:absolute motion-safe:inline-flex h-full w-full motion-safe:animate-ping rounded-full bg-success opacity-75" />
                            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
                          </span>
                          {cameraCount} LIVE
                        </span>
                      )}

                      {showBreachBadge && (
                        <span
                          className={cn(
                            BADGE_BASE,
                            'border-danger/40 bg-danger/15 text-danger motion-safe:animate-pulse',
                          )}
                        >
                          {criticalEventCount} BREACH{criticalEventCount === 1 ? '' : 'ES'}
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* System Status -- every line here is real: isApiConnected mirrors
            whether the last listCameras() call actually succeeded, cameraCount
            is the real registered-camera count, and "PostgreSQL 16" is a
            static architecture fact (not a live per-request health check --
            there's no dedicated DB-health endpoint to poll for that). */}
        <div className="mx-1 mt-3 flex flex-col gap-1.5 rounded-md border border-border/40 bg-surface/5 px-2.5 py-2 text-[10px]">
          <div className="flex items-center justify-between">
            <span className="text-ink-on-dark-subtle">System</span>
            <span className={cn('flex items-center gap-1 font-medium', isApiConnected ? 'text-success' : 'text-danger')}>
              <span className={cn('h-1.5 w-1.5 rounded-full', isApiConnected ? 'bg-success' : 'bg-danger')} />
              {isApiConnected ? 'Operational' : 'Offline'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-ink-on-dark-subtle">Feeds</span>
            <span className="font-mono text-ink-on-dark font-semibold tabular-nums">
              {cameraCount}
            </span>
          </div>
          <div className="flex items-center justify-between border-t border-border/30 pt-1.5 mt-0.5">
            <span className="text-ink-on-dark-subtle">Backend</span>
            <span className="font-mono text-ink-on-dark-quiet">PostgreSQL 16</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
