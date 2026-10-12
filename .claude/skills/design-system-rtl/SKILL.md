---
name: design-system-rtl
description: Visual and RTL/Hebrew design rules for the carinfo-bot Mini App - tokens, glassmorphism card recipe, buttons, spacing, typography, bidi handling for plates/prices/phones, mobile and Telegram WebView constraints, states, accessibility, and a pre-merge design checklist. Use when designing or reviewing any UI.
---

# Design system cheat-sheet (source of truth: `webapp/src/styles.css`)

## Tokens
`--primary #007aff` | `--secondary #34c759` | `--danger #ff3b30` | `--text-main #1d1d1f` | `--text-muted #86868b` | `--bg #f0f4f8` | `--bg-card #fff` | `--border rgba(0,100,200,.08)` | `--shadow 0 10px 32px rgba(0,50,150,.07)` | `--radius 20px`. Font: Heebo. Body `direction: rtl`, max content width 480.
Tier colours (packages, by index%3): Silver `#1e40af->#0ea5e9`/accent `#38bdf8`; Gold `#92400e->#f59e0b`/`#fbbf24`; Platinum `#4c1d95->#a855f7`/`#c084fc`.
Add a new token to `:root` before using a new colour twice.

## Recipes
- **Card**: class `card` (glass: translucent white, blur, subtle border, soft shadow, radius 20). Page padding 24; vertical rhythm multiples of 4 (8/12/16/24).
- **Primary action**: `.btn` full width, one per view; secondary `.btn-secondary`/`.btn-outline`; destructive `.btn-danger` + confirm.
- **Hierarchy**: title (`.page-title`) -> key figure (large, weight 700-900) -> label (muted, 12-13px) -> detail rows (`.info-row`).
- **Status colours**: success green, warning amber `#f59e0b`, danger red; always pair with an icon/text.
- **Motion**: `.page-enter` on screen mount; 150-250ms ease for hover/press; honour `prefers-reduced-motion`.

## Hebrew & RTL rules
- Direction flips layouts: first child is on the RIGHT. "←" = back, "→" = forward.
- LTR islands inside RTL text: plates (`12-345-67`), phone numbers, prices (`₪25`), emails, URLs, English brand names -> `<span dir="ltr">` or `style={{unicodeBidi:'isolate', direction:'ltr'}}`. Test with a number at start/end of a Hebrew sentence.
- Currency symbol ₪ placement: keep `₪25` as one isolated unit.
- Use `text-align: start`/`end` thinking; `gap` instead of left/right margins; avoid hard-coded `left/right` unless intended.
- Copy: short, polite, second person singular-neutral; no machine-translated phrasing; plural/gender-neutral wording where possible (e.g. "נותרו 5 בדיקות").
- Dates `dd/mm/yyyy` via `utils/time.js`; numbers with thousands separator.
- The `LicensePlate` component renders the Israeli yellow plate - reuse it, don't restyle.

## Mobile / Telegram
- Design for 390x844; test also 360 and 430. No horizontal scroll. Tap targets >= 44px.
- Fixed `BottomNav` height must be reserved (padding-bottom) on screens that show it; respect safe-area (`env(safe-area-inset-bottom)`).
- Inside Telegram the header/back are native: our `BackButton` card is the in-page back; keep both consistent with `goBack`.
- Inputs: `font-size >= 16px` (prevents iOS zoom); `inputMode="numeric"` for plates/phones; clear button; no layout jump when keyboard opens.

## States & feedback
loading (skeleton) - empty (illustration/emoji + Hebrew sentence + CTA) - error (what happened + retry) - success (toast/inline confirmation). Disable buttons while submitting and show progress. Optimistic UI only if rollback is handled.

## Accessibility
Contrast >= 4.5:1 (muted `#86868b` on white is borderline: only for secondary text >= 13px). `aria-label` on icon buttons, visible focus ring, don't convey meaning by colour alone.

## Pre-merge design checklist
- [ ] only tokens/classes from this system; no stray hex values
- [ ] RTL correct incl. arrows, bidi islands, truncation (`text-overflow: ellipsis` with `min-width: 0` in flex)
- [ ] all 4 states + long Hebrew text + 0/1/many items
- [ ] 390px screenshot reviewed (use `qa-verify-change` smoke `--shot`)
- [ ] no blank screen on empty/partial API data
- [ ] build passes; diff is surgical (`git diff --stat`)
