import { useState } from 'react'
import {
  LayoutDashboard,
  Radio,
  Camera,
  ShieldAlert,
  SearchCheck,
  BrainCircuit,
  BellRing,
  BarChart3,
  Cpu,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { TraceLogo } from '@/components/TraceLogo'

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
      { id: 'agent', label: 'Vision Agent', icon: BrainCircuit, badge: 'AI COPILOT' },
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

/** Micro count indicator -- a plain neutral chip, not a colored pill. Real
 * violations still read in rose text (--color-danger) inside it; everything
 * else (live count, the static "AI COPILOT" label) stays neutral, per the
 * 90/10 rule: color is reserved for what's actually a confirmed breach. */
const BADGE_BASE = 'flex items-center gap-1 rounded bg-white/[0.05] text-[10px] font-mono text-ink-on-dark-subtle px-1.5 py-0.5 shrink-0'

/**
 * Three operational groups (Real-Time Surveillance / Forensic Intelligence /
 * Analytics & Engine), collapsible into an icon-only rail, plus a real
 * system-status footer. Every badge here is real, already-available data --
 * there is deliberately no FPS/CPU reading or pending-action count anywhere
 * in the nav/footer: neither is computed or exposed anywhere the frontend
 * can read yet (no list/count endpoint exists for pending agent actions, and
 * per-camera FPS was already established as unavailable when the header's
 * telemetry strip was built -- see CamerasView.tsx's own note on that).
 */
export function Sidebar({ activeView, onNavigate, cameraCount = 0, isApiConnected = true, criticalEventCount = 0 }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      aria-label="Sidebar Navigation"
      className={cn(
        'flex h-screen shrink-0 flex-col border-r border-border bg-primary text-ink-on-dark select-none transition-[width] duration-200 ease-out',
        collapsed ? 'w-20' : 'w-64',
      )}
    >
      {/* Brand -- TraceLogo is real inline SVG (not the old static
          public/trace-symbol.svg, which had its own hardcoded colors baked
          in, disconnected from tokens.css), so it renders in the live theme
          and covers both the expanded and collapsed-rail states itself. */}
      <div
        className={cn(
          'flex shrink-0 items-center border-b border-border/20 transition-all',
          collapsed ? 'h-20 flex-col justify-center gap-1.5 px-2' : 'h-12 flex-row justify-between px-3.5',
        )}
      >
        <TraceLogo collapsed={collapsed} />

        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-ink-on-dark-subtle hover:bg-surface/10 hover:text-ink-on-dark transition-colors"
        >
          {collapsed ? <PanelLeftOpen className="h-3.5 w-3.5" /> : <PanelLeftClose className="h-3.5 w-3.5" />}
        </button>
      </div>

      {/* Main Navigation */}
      <div className="flex flex-1 flex-col justify-between overflow-y-auto overflow-x-visible px-2 py-3">
        <nav className="flex flex-col gap-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="flex flex-col gap-1">
              {collapsed ? (
                <div className="mx-2 my-1 border-t border-border/25" />
              ) : (
                // text-ink-disabled (zinc-600) is a deliberately dim choice
                // for these category headers specifically, not a "disabled"
                // control -- matches this design system's own spec.
                <span className="px-3 mb-1 text-[10px] font-mono font-medium tracking-widest text-ink-disabled uppercase">
                  {group.title}
                </span>
              )}

              <div className="flex flex-col gap-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon
                  const isActive = activeView === item.id
                  const showLiveBadge = item.id === 'live' && cameraCount > 0
                  const showBreachBadge = item.id === 'events' && criticalEventCount > 0
                  const badgeText = item.badge ?? (showLiveBadge ? `${cameraCount} LIVE` : showBreachBadge ? `${criticalEventCount} BREACH${criticalEventCount === 1 ? '' : 'ES'}` : undefined)

                  return (
                    <div key={item.id} className="group/navitem relative">
                      {/* Crisp detached active indicator (collapsed rail
                          only) -- a border-l on the rounded button itself
                          rendered as a curved bracket/arc where the border
                          met the rounded corner, so this is a separate
                          floating pill instead, unaffected by the button's
                          own border-radius. */}
                      {collapsed && isActive && (
                        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-accent rounded-r-full shadow-[0_0_8px_var(--color-accent)]" />
                      )}

                      <button
                        type="button"
                        onClick={() => onNavigate(item.id)}
                        aria-current={isActive ? 'page' : undefined}
                        aria-label={collapsed ? item.label : undefined}
                        className={cn(
                          'relative flex w-full items-center text-xs font-medium transition-all rounded-md',
                          'focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-1',
                          collapsed ? 'justify-center px-0 py-2.5' : 'justify-between px-2.5 py-1.5',
                          !collapsed && (isActive ? 'border-l-2 border-l-accent' : 'border-l-2 border-l-transparent'),
                          isActive
                            ? 'bg-white/[0.06] text-ink-on-dark font-medium'
                            : 'text-ink-on-dark-quiet hover:bg-white/[0.04] hover:text-ink-on-dark',
                        )}
                      >
                        <div className={cn('flex items-center min-w-0', collapsed ? 'justify-center' : 'gap-2.5')}>
                          {collapsed ? (
                            <span className="relative flex h-8 w-8 shrink-0 items-center justify-center">
                              <Icon
                                className={cn(
                                  'h-[22px] w-[22px] transition-colors',
                                  isActive ? 'text-accent' : 'text-ink-on-dark-quiet group-hover/navitem:text-ink-on-dark',
                                )}
                              />
                              {/* Corner dot sits on the icon's own box, not
                                  the full-width button -- pinned to this
                                  fixed-size wrapper instead of `right-2` on
                                  the row (which floated near the rail's outer
                                  edge, far from the icon it was meant to
                                  annotate). */}
                              {badgeText && (
                                <span
                                  className={cn(
                                    'absolute top-1 right-1 h-2 w-2 rounded-full ring-2 ring-primary',
                                    showBreachBadge ? 'bg-danger' : showLiveBadge ? 'bg-success' : 'bg-accent',
                                  )}
                                />
                              )}
                            </span>
                          ) : (
                            <Icon
                              className={cn(
                                'h-3.5 w-3.5 shrink-0 transition-colors',
                                isActive ? 'text-accent' : 'text-ink-on-dark-quiet group-hover/navitem:text-ink-on-dark',
                              )}
                            />
                          )}
                          {!collapsed && <span className="truncate">{item.label}</span>}
                        </div>

                        {!collapsed && badgeText && (
                          <span className={cn(BADGE_BASE, showBreachBadge && 'text-danger')}>
                            {showLiveBadge && <span className="h-1.5 w-1.5 rounded-full bg-success" />}
                            {badgeText}
                          </span>
                        )}
                      </button>

                      {collapsed && (
                        <div
                          role="tooltip"
                          className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 flex -translate-y-1/2 items-center gap-1.5 whitespace-nowrap rounded border border-border bg-primary px-2.5 py-1 font-mono text-xs text-ink-on-dark opacity-0 shadow-md transition-opacity duration-150 group-hover/navitem:opacity-100"
                        >
                          {item.label}
                          {badgeText && (
                            <span className={cn('rounded bg-white/[0.05] px-1 py-0.2 text-[9px] text-ink-on-dark-subtle', showBreachBadge && 'text-danger')}>
                              {badgeText}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
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
            there's no dedicated DB-health endpoint to poll for that).
            Collapsed rail shrinks this to a single status dot with the full
            detail moved into its hover tooltip. */}
        {collapsed ? (
          <div className="group/status relative mx-auto mt-3 pb-6 flex h-8 w-8 items-center justify-center">
            <span className={cn('h-1.5 w-1.5 rounded-full', isApiConnected ? 'bg-success' : 'bg-danger')} />
            <div
              role="tooltip"
              className="pointer-events-none absolute left-full bottom-0 z-50 ml-2 flex flex-col gap-1 whitespace-nowrap rounded border border-border bg-primary px-2.5 py-1.5 font-mono text-[11px] text-ink-on-dark opacity-0 shadow-md transition-opacity duration-150 group-hover/status:opacity-100"
            >
              <span className={isApiConnected ? 'text-success' : 'text-danger'}>
                System: {isApiConnected ? 'Operational' : 'Offline'}
              </span>
              <span className="text-ink-on-dark-quiet">Feeds: {cameraCount}</span>
              <span className="text-ink-on-dark-quiet">Backend: PostgreSQL 16</span>
            </div>
          </div>
        ) : (
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
        )}
      </div>
    </aside>
  )
}
