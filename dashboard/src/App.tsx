/**
 * App shell placeholder: Header + Sidebar, built from TRACE's design tokens
 * (theme/tokens.css via the CSS variable mapping in index.css), not
 * hardcoded colors. Content area is empty -- real dashboard views come later.
 *
 * The header's "TRACE" mark is a TEXT placeholder, not the real logo/
 * wordmark asset -- no logo file has been provided yet (checked the whole
 * repo, nothing found). Swap <Wordmark /> below for the real asset once
 * it's sent.
 */

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

function Sidebar() {
  const navItems = ['Dashboard', 'Cameras', 'Events', 'Analytics']

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col bg-primary text-surface">
      <div className="flex h-16 items-center px-6 text-sm font-medium tracking-wide text-accent">
        Navigation
      </div>
      <nav className="flex flex-col gap-1 px-3">
        {navItems.map((item, i) => (
          <a
            key={item}
            href="#"
            className={
              'rounded-md px-3 py-2 text-sm transition-colors hover:bg-secondary ' +
              (i === 0 ? 'bg-secondary text-surface' : 'text-surface/80')
            }
          >
            {item}
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
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-auto p-6">
          <div className="rounded-lg border border-border bg-surface p-6 text-secondary">
            Content area placeholder — dashboard views land here.
          </div>
        </main>
      </div>
    </div>
  )
}

export default App
