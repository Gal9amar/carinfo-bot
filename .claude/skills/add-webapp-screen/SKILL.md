---
name: add-webapp-screen
description: Step-by-step for adding a new screen/page to the carinfo-bot React Mini App - page component, registering it in App.jsx's screen state machine, navigation entry points, data loading with loading/empty/error states, lazy loading, and verification. Use whenever a new page, tab or modal-sized view is requested.
---

# Add a screen

The app has **no router**. `webapp/src/App.jsx` holds `screen` (string) and `screenStack`; `navigate(name)` pushes, `goBack()` pops (Telegram BackButton is wired to it). Screens render as `if (screen === 'x') return (...)` blocks.

## Steps
1. **Create** `webapp/src/pages/FooPage.jsx` with `export default function FooPage({ onBack, onNavigate, user })`. Start with `<div className="page"><BackButton onClick={onBack} /><div className="page-title">🧩 כותרת</div>...`.
2. **Data**: add the fetch function in `webapp/src/api.js` first (use `add-api-endpoint`); load in `useEffect`, store `null` = loading, handle failure (`.catch`) -> error state with retry. Guard arrays: `Array.isArray(x) ? x : []`.
3. **States**: skeleton/`.loading` while loading, friendly Hebrew empty state with a next-action button, error with retry, then content. Never render blank.
4. **Register** in `App.jsx`: import (use `lazy()` + `<Suspense fallback={<div className="loading" />}>` if the page is big/rare, like AdminPage), add a `screen === 'foo'` block wrapped in `<div key="foo" className="page-enter">`; add `<BottomNav screen={screen} onNavigate={navigate} />` as a sibling only if it should show the tabs (see how `history`/`profile` do it) and give the page bottom padding so content clears the bar.
5. **Entry points**: a tile in `ProfilePage.jsx` `tiles` array, a button on `HomePage`, or a deep link: add `if (page === 'foo') { setScreen('foo'); return }` next to the other `?page=` handlers in App.jsx (bot buttons can open `WEBAPP_URL?page=foo`).
6. **Style**: reuse `.card`, `.btn*`, `.info-row`, `.input`; tokens from `:root`; follow `design-system-rtl`.
7. **Build + smoke**: `cd webapp && npm run build`, then `qa-verify-change` step 5 with the click path to your screen. View the screenshot.

## Gotchas
- A `lazy()` page MUST have a default export, otherwise the screen is blank (React error #306).
- Don't call `window.Telegram.WebApp.X` unguarded - the app also runs in a plain browser/test.
- Admin-only screens: also protect the API (`_require_admin`); hiding the tile is not security.
- Keep copy Hebrew; keep numbers/prices/plates LTR-isolated.
