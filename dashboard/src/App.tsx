/**
 * App shell: Header + Sidebar, built from TRACE's design tokens
 * (theme/tokens.css via the CSS variable mapping in index.css), not
 * hardcoded colors. Content area switches between the Live/Video view
 * (Phase 10.1) and the Analytics view (Phase 10.2) via plain local state --
 * no router dependency, since the dashboard only has these two real views
 * so far ("Cameras"/"Events" nav items remain inert placeholders).
 *
 * The header's "TRACE" mark is a TEXT placeholder, not the real logo/
 * wordmark asset -- no logo file has been provided yet (checked the whole
 * repo, nothing found). Swap <Wordmark /> below for the real asset once
 * it's sent.
 */

import { useState } from 'react'
import { LiveView } from '@/components/LiveView'
import { AnalyticsView } from '@/components/AnalyticsView'

type ActiveView = 'dashboard' | 'analytics'

function Wordmark() {
  return (
    <span className="group inline-flex items-center gap-2 text-lg font-semibold tracking-wide text-surface">
      <span
        aria-hidden
        className="h-2 w-2 rounded-full bg-accent transition-transform duration-700 ease-out group-hover:scale-150 animate-pulse"
      />
      <span className="animate-in fade-in slide-in-from-left-2 duration-700">
        TRACE
      </span>
    </span>
  )
}

interface SidebarProps {
  activeView: ActiveView
  onNavigate: (view: ActiveView) => void
}

function Sidebar({ activeView, onNavigate }: SidebarProps) {
  const navItems: { label: string; view: ActiveView | null }[] = [
    { label: 'Dashboard', view: 'dashboard' },
    { label: 'Cameras', view: null },
    { label: 'Events', view: null },
    { label: 'Analytics', view: 'analytics' },
  ]

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col bg-primary text-surface">
      <div className="flex h-16 items-center px-6 text-sm font-medium tracking-wide text-accent">
        Navigation
      </div>
      <nav className="flex flex-col gap-1 px-3">
        {navItems.map((item) => (
          <a
            key={item.label}
            href="#"
            onClick={(event) => {
              event.preventDefault()
              if (item.view) onNavigate(item.view)
            }}
            className={
              'rounded-md px-3 py-2 text-sm transition-colors hover:bg-secondary ' +
              (item.view === activeView ? 'bg-secondary text-surface' : 'text-surface/80')
            }
          >
            {item.label}
          </a>
        ))}
      </nav>
    </aside>
  )
}

function Header() {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border bg-primary px-6">
      <Wordmark />
      <span className="text-sm text-surface/70">Video Intelligence Dashboard</span>
    </header>
  )
}

function App() {
  const [activeView, setActiveView] = useState<ActiveView>('dashboard')

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <Sidebar activeView={activeView} onNavigate={setActiveView} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto p-6">
          {activeView === 'dashboard' ? <LiveView /> : <AnalyticsView />}
        </main>
      </div>
    </div>
  )
}

export default App
