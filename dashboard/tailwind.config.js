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
    },
  },
  plugins: [],
};
