/**
 * TRACE dashboard Tailwind config.
 *
 * theme.colors is fully REPLACED (not extended) -- Tailwind's default
 * palette (red-500, blue-200, ...) is deliberately unavailable, so there is
 * no ad-hoc-hex escape hatch: every color utility a component can reach for
 * comes from theme/tokens.css. Each entry below points at that file's CSS
 * variables rather than duplicating the hex values here, so tokens.css stays
 * the one place brand/semantic colors are actually defined.
 *
 * Danger/success/warning/info are semantic states, reserved for event
 * badges, alert toasts, status dots, and violation-vs-normal chart series --
 * never a substitute for the brand palette elsewhere. See tokens.css for the
 * full rationale.
 */
module.exports = {
  content: ["./src/**/*.{html,js,jsx,ts,tsx}"],
  theme: {
    colors: {
      transparent: "transparent",
      current: "currentColor",

      // Brand
      primary: "var(--color-primary)",
      secondary: "var(--color-secondary)",
      accent: "var(--color-accent)",
      "surface-alt": "var(--color-surface-alt)",
      border: "var(--color-border)",
      background: "var(--color-background)",
      surface: "var(--color-surface)",

      // Semantic states
      success: "var(--color-success)",
      warning: "var(--color-warning)",
      danger: "var(--color-danger)",
      info: "var(--color-info)",

      // Text hierarchy ("ink" scale) -- deliberately its own namespace, not
      // reusing `primary`/`secondary` above: those are brand/interactive
      // colors (buttons, active nav), these are neutral text tiers. See
      // tokens.css for the contrast ratio each one targets.
      ink: "var(--text-primary)",
      "ink-quiet": "var(--text-secondary)",
      "ink-subtle": "var(--text-tertiary)",
      "ink-disabled": "var(--text-disabled)",

      // Same tiers, for text on a --color-primary (navy) surface -- the
      // sidebar and the video-player HUD chips.
      "ink-on-dark": "var(--text-on-dark)",
      "ink-on-dark-quiet": "var(--text-on-dark-quiet)",
      "ink-on-dark-subtle": "var(--text-on-dark-subtle)",
    },
  },
  plugins: [],
};
