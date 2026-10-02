# 0011. Frontend styling: Tailwind, theme tokens and light/dark mode

- Status: Accepted
- Date: 2026-10-02

## Context

The first frontend screens were unstyled HTML, and the delete confirmation used the
browser's own pop-up. The owner wants an airy, elegant look (cobalt with an orange
accent, soft rounded cards, lots of empty space) in both a light and a dark theme,
and is not a designer. Two sets of mockups were compared before this decision.

## Options considered

- **Hand-written CSS with design tokens.** Fewest dependencies, but a lot of
  repetitive work to look polished, and accessible pieces (dialogs) must be built by
  hand.
- **A full component library** (for example Material UI). Quick, but it looks like
  the library, and fights a custom look.
- **Tailwind CSS plus a few accessible primitives.** Utility classes keep styling
  next to the markup, theme values live in CSS variables, and Radix supplies a
  correct accessible dialog. This is also the combination behind most polished
  AI-generated UIs.

## Decision

- **Tailwind CSS v4** (CSS-first config, with the Vite plugin).
- **Color roles, not raw colors.** `src/index.css` defines roles (background, card,
  border, foreground, muted, primary, accent, destructive, and so on) once for light
  and once for dark. Screens use only role names, so a theme switch swaps the values.
- **Dark mode** is a `dark` class on `<html>`. A small script in `index.html` sets it
  before the page paints (no white flash). `src/theme.ts` follows the system setting
  until the user flips the toggle, and then remembers the choice in local storage.
- **Radix `AlertDialog`** for the in-page "are you sure?" box, **Lucide** icons, and
  **self-hosted fonts** (Bricolage Grotesque for headings, Figtree for text) through
  Fontsource, so no font service is called at runtime.
- **A small `src/ui/` folder** (Button, Card, fields, ConfirmDialog, and so on) holds
  the reusable pieces. Screens live in `src/pages/`.
- **No browser pop-ups** (`alert`, `confirm`, `prompt`) anywhere in the app.

## Consequences

- One place to change the look (the tokens), and light and dark stay in step.
- Six new frontend dependencies (Tailwind, its Vite plugin, Radix alert dialog,
  Lucide, and two font packages). All are widely used and work with React 19 and
  Vite 8 here.
- Contrast was chosen by eye and by calculation for the mockups, not tested with a
  tool. An accessibility check (keyboard use, screen reader, contrast) is still to do.
- The pages are responsive by Tailwind's defaults but have only been looked at on a
  desktop-width browser so far.
