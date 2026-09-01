import {
  LayoutDashboard,
  Video,
  Activity,
  BarChart3,
  Search,
  ShieldAlert,
  Bot,
  Radio,
  Sliders,
  CheckCircle2,
} from 'lucide-react'
import { cn } from '@/lib/utils'

export type ActiveView = 'dashboard' | 'cameras' | 'events' | 'analytics' | 'investigations' | 'alerts' | 'agent'

interface NavItem {
  id: ActiveView
  label: string
  icon: typeof LayoutDashboard
  badge?: string
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'cameras', label: 'Cameras', icon: Video },
  { id: 'events', label: 'Events', icon: Activity },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'investigations', label: 'Investigations', icon: Search },
  { id: 'alerts', label: 'Alerts', icon: ShieldAlert },
  { id: 'agent', label: 'Vision Agent', icon: Bot, badge: 'AI' },
]

interface SidebarProps {
  activeView: ActiveView
  onNavigate: (view: ActiveView) => void
  cameraCount?: number
  isApiConnected?: boolean
}

export function Sidebar({ activeView, onNavigate, cameraCount = 0, isApiConnected = true }: SidebarProps) {
  return (
    <aside
      aria-label="Sidebar Navigation"
      className="flex h-screen w-60 shrink-0 flex-col border-r border-border/40 bg-primary text-surface select-none"
    >
      {/* Brand Header */}
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-border/20 px-4">
        <div className="flex items-center gap-2.5">
          <div className="relative flex h-7 w-7 items-center justify-center rounded-md bg-surface/10 ring-1 ring-white/10">
            <Radio className="h-3.5 w-3.5 text-accent animate-pulse" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-wider text-surface leading-none">
              TRACE
            </span>
            <span className="text-[9px] font-medium tracking-wider text-accent/80 uppercase mt-0.5">
              Video Intelligence
            </span>
          </div>
        </div>
        <span className="rounded bg-surface/10 px-1.5 py-0.5 text-[9px] font-mono text-accent/90">
          v2.4
        </span>
      </div>

      {/* Main Navigation */}
      <div className="flex flex-1 flex-col justify-between overflow-y-auto px-2.5 py-3">
        <div className="flex flex-col gap-1">
          <div className="px-2.5 pb-1.5 text-[9px] font-semibold uppercase tracking-wider text-accent/60">
            Operations
          </div>
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
                      ? 'bg-secondary text-surface'
                      : 'text-surface/75 hover:bg-surface/10 hover:text-surface active:scale-[0.99]',
                  )}
                >
                  <div className="flex items-center gap-2.5">
                    <Icon
                      className={cn(
                        'h-3.5 w-3.5 transition-colors',
                        isActive ? 'text-surface' : 'text-accent/80 group-hover:text-surface',
                      )}
                    />
                    <span>{item.label}</span>
                  </div>

                  {item.badge && (
                    <span className="rounded bg-accent/20 px-1 py-0.2 text-[9px] font-mono text-accent">
                      {item.badge}
                    </span>
                  )}

                  {isActive && (
                    <span
                      aria-hidden="true"
                      className="absolute right-1 h-3 w-1 rounded-full bg-accent"
                    />
                  )}
                </button>
              )
            })}
          </nav>
        </div>

        {/* System Status / Health Card */}
        <div className="flex flex-col gap-2 pt-3 border-t border-border/15">
          <div className="rounded-md border border-border/15 bg-surface/5 p-2.5">
            <div className="flex items-center justify-between pb-1.5">
              <span className="text-[10px] font-medium tracking-wide text-surface/70">
                System Health
              </span>
              <span className="flex items-center gap-1 text-[10px] font-medium text-success">
                <CheckCircle2 className="h-3 w-3" />
                {isApiConnected ? 'Operational' : 'Offline'}
              </span>
            </div>
            <div className="flex items-center justify-between border-t border-border/10 pt-1.5 text-[10px] text-surface/60">
              <span>Connected Feeds</span>
              <span className="font-mono text-surface font-semibold tabular-nums">
                {cameraCount}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between px-1.5 text-[10px] text-surface/40">
            <span>Operator Station</span>
            <Sliders className="h-3 w-3 text-accent/50" />
          </div>
        </div>
      </div>
    </aside>
  )
}
