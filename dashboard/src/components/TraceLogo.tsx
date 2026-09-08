interface TraceLogoProps {
  collapsed?: boolean
  className?: string
}

/**
 * The TRACE brand mark: a bounding-reticle "T" drawn as real inline SVG
 * (not a static asset), so it renders in the live theme tokens instead of
 * hardcoded colors baked into an image file -- the old public/trace-symbol.svg
 * had exactly that problem (its own fixed #9AA5B4/#00AEEF, disconnected from
 * tokens.css, from a previous brand iteration). One component covers both
 * the expanded sidebar (icon + wordmark) and the collapsed rail (icon only)
 * via `collapsed`, replacing what used to be two separate implementations.
 */
export function TraceLogo({ collapsed = false, className = '' }: TraceLogoProps) {
  return (
    <div className={`group flex items-center gap-3 select-none ${className}`}>
      {/* Tactical Reticle Mark */}
      <div className="relative flex items-center justify-center w-8 h-8 rounded-md bg-primary border border-white/10 group-hover:border-accent/40 transition-colors shrink-0">
        <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-5 h-5">
          {/* Outer Corner Reticles (Bounding Box Brackets) */}
          <path d="M 4 9 V 4 H 9" className="stroke-ink-on-dark-subtle" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M 23 4 H 28 V 9" className="stroke-ink-on-dark-subtle" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M 4 23 V 28 H 9" className="stroke-ink-on-dark-subtle" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M 23 28 H 28 V 23" className="stroke-ink-on-dark-subtle" strokeWidth="1.5" strokeLinecap="round" />

          {/* Central Structural "T" with Trajectory Accent */}
          <path d="M 8 11 H 24" className="stroke-ink-on-dark" strokeWidth="2" strokeLinecap="round" />
          <path d="M 16 11 V 22" className="stroke-ink-on-dark" strokeWidth="2" strokeLinecap="round" />

          {/* Spatial Anchor Point -- the one reserved accent-cyan use here */}
          <circle cx="16" cy="11" r="1.5" className="fill-accent" />
        </svg>
      </div>

      {/* Wordmark -- hidden when the sidebar is collapsed to a rail */}
      {!collapsed && (
        <div className="flex flex-col justify-center min-w-0">
          <div className="flex items-center gap-1.5">
            {/* Geist Variable pinned inline on purpose -- a separate,
                deliberate brand choice that must not follow --font-sans
                (Exo 2) when the general UI typeface changes. */}
            <span
              className="text-sm font-bold tracking-[0.2em] text-ink-on-dark uppercase"
              style={{ fontFamily: "'Geist Variable', sans-serif" }}
            >
              TRACE
            </span>
            <span className="w-1.5 h-1.5 rounded-full bg-accent/80 shrink-0" />
          </div>
          <span className="font-mono text-[8px] tracking-[0.15em] text-ink-on-dark-subtle uppercase -mt-0.5">
            Spatial Intelligence
          </span>
        </div>
      )}
    </div>
  )
}
