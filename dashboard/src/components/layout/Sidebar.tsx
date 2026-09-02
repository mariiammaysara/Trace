import {
  LayoutDashboard,
  Video,
  Activity,
  BarChart3,
  Search,
  ShieldAlert,
  Bot,
  MonitorPlay,
  FlaskConical,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export type ActiveView = 'dashboard' | 'live' | 'cameras' | 'events' | 'analytics' | 'investigations' | 'alerts' | 'agent' | 'evaluation'

interface NavItem {
  id: ActiveView
  label: string
  icon: typeof LayoutDashboard
  badge?: string
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Overview', icon: LayoutDashboard },
  { id: 'live', label: 'Live', icon: MonitorPlay },
  { id: 'cameras', label: 'Cameras', icon: Video },
  { id: 'events', label: 'Events', icon: Activity },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'investigations', label: 'Investigation', icon: Search },
  { id: 'alerts', label: 'Alerts', icon: ShieldAlert },
  { id: 'agent', label: 'Vision Agent', icon: Bot, badge: 'AI' },
  { id: 'evaluation', label: 'Evaluation', icon: FlaskConical },
]

interface SidebarProps {
  activeView: ActiveView
  onNavigate: (view: ActiveView) => void
  cameraCount?: number
  isApiConnected?: boolean
}

/**
 * Deliberately restrained: the navy fill is the TRACE brand surface, but it
 * should read as a quiet instrument panel, not the loudest thing on screen.
 * No boxed logo mark, no nested "card" for system health -- just text rows
 * at a size that stays out of the way of the content next to it.
 */
export function Sidebar({ activeView, onNavigate, cameraCount = 0, isApiConnected = true }: SidebarProps) {
  return (
    <aside
      aria-label="Sidebar Navigation"
      className="flex h-screen w-52 shrink-0 flex-col border-r border-border/40 bg-primary text-ink-on-dark select-none"
    >
      {/* Brand -- symbol from brand/symbol-color-on-dark.svg (public/trace-symbol.svg);
          wordmark stays live text rather than baked into the SVG so it renders in
          the app's actual Geist webfont instead of falling back to a system sans
          (an externally-loaded <img> SVG can't see the page's web fonts). */}
      <div className="flex h-12 shrink-0 items-center gap-2 border-b border-border/20 px-3.5">
        <img src="/trace-symbol.svg" alt="" className="h-4 w-4 shrink-0" />
        <span className="text-sm font-semibold tracking-wide text-ink-on-dark leading-none">
          TRACE
        </span>
      </div>

      {/* Main Navigation */}
      <div className="flex flex-1 flex-col justify-between overflow-y-auto px-2 py-2.5">
        <nav className="flex flex-col gap-0.5">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon
            const isActive = activeView === item.id

            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onNavigate(item.id)}
                aria-current={isActive ? 'page' : undefined}
                className={cn(
                  'group relative flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors',
                  'focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-1',
                  isActive
                    ? 'bg-secondary text-ink-on-dark'
                    : 'text-ink-on-dark-quiet hover:bg-surface/10 hover:text-ink-on-dark',
                )}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    className={cn(
                      'h-3.5 w-3.5 transition-colors',
                      isActive ? 'text-ink-on-dark' : 'text-accent group-hover:text-ink-on-dark',
                    )}
                  />
                  <span>{item.label}</span>
                </div>

                {item.badge && (
                  <span className="rounded bg-accent/20 px-1 py-0.2 text-[9px] font-mono text-accent">
                    {item.badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        {/* System Health -- plain rows, no nested card chrome */}
        <div className="flex flex-col gap-1 border-t border-border/15 px-2.5 pt-2.5 text-[10px]">
          <div className="flex items-center justify-between">
            <span className="text-ink-on-dark-subtle">System</span>
            <span className={cn('font-medium', isApiConnected ? 'text-success' : 'text-danger')}>
              {isApiConnected ? 'Operational' : 'Offline'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-ink-on-dark-subtle">Feeds</span>
            <span className="font-mono text-ink-on-dark font-semibold tabular-nums">
              {cameraCount}
            </span>
          </div>
        </div>
      </div>
    </aside>
  )
}
