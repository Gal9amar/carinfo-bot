// Real-browser smoke test against the local API (local_api.py) serving webapp/dist.
// Usage: node smoke_ui.mjs [--user 1] [--port 8099] [--shot out.png] "click text 1" "click text 2" ...
// Each positional arg is visible text to click, in order (e.g. "אזור אישי" "פאנל ניהול").
// Fails (exit 1) on any uncaught page error, console.error, or failed same-origin request / 5xx.
// Requires: webapp built (cd webapp && npm ci && npm run build), playwright-core resolvable
// (cd webapp && npm i --no-save playwright-core), Chromium at $PLAYWRIGHT_BROWSERS_PATH or /opt/pw-browsers/chromium.
import { execFileSync } from 'node:child_process'
import { createRequire } from 'node:module'
import path from 'node:path'
const require = createRequire(path.resolve('webapp/package.json'))
const { chromium } = require('playwright-core')

const argv = process.argv.slice(2)
const opt = (n, d) => { const i = argv.indexOf(n); if (i < 0) return d; const v = argv[i + 1]; argv.splice(i, 2); return v }
const user = opt('--user', '1'), port = opt('--port', '8099'), shot = opt('--shot', '')
const steps = argv
const base = `http://127.0.0.1:${port}`
const initData = execFileSync('python3', [new URL('./sign_init_data.py', import.meta.url).pathname, user]).toString().trim()

const b = await chromium.launch({ executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium', args: ['--no-sandbox'] })
const pg = await b.newPage({ viewport: { width: 390, height: 844 } }) // phone width, Telegram-like
const errs = []
pg.on('pageerror', e => errs.push('PAGEERROR ' + e.message))
pg.on('console', m => { if (m.type() === 'error' && !/telegram\.org|ERR_TUNNEL|ERR_NAME_NOT_RESOLVED|fonts\.g/.test(m.text())) errs.push('CONSOLE ' + m.text().slice(0, 300)) })
pg.on('response', r => { if (r.url().startsWith(base) && r.status() >= 500) errs.push(`HTTP ${r.status()} ${r.url()}`) })
// Telegram's own script is blocked in sandboxes; stub the bits the app calls.
await pg.route(/telegram\.org\/js/, r => r.fulfill({ contentType: 'text/javascript', body: '' }))
await pg.addInitScript(id => {
  const noop = () => {}
  window.Telegram = { WebApp: { initData: id, initDataUnsafe: {}, expand: noop, ready: noop, close: noop, openLink: noop,
    openTelegramLink: noop, disableVerticalSwipes: noop, enableClosingConfirmation: noop, setHeaderColor: noop,
    setBackgroundColor: noop, isVersionAtLeast: () => true, platform: 'ios', colorScheme: 'light', themeParams: {},
    BackButton: { show: noop, hide: noop, onClick: noop, offClick: noop },
    MainButton: { show: noop, hide: noop, setParams: noop, onClick: noop, offClick: noop },
    HapticFeedback: { impactOccurred: noop, notificationOccurred: noop, selectionChanged: noop } } }
}, initData)

await pg.goto(base + '/'); await pg.waitForTimeout(2000)
const text = async () => (await pg.innerText('body')).replace(/\s+/g, ' ').trim()
console.log('START :', (await text()).slice(0, 160))
for (const s of steps) {
  const loc = pg.getByText(s).last()
  if (!(await loc.count())) { errs.push(`NOT FOUND text "${s}"`); break }
  await loc.click(); await pg.waitForTimeout(2000)
  console.log(`AFTER "${s}":`, (await text()).slice(0, 160))
}
if ((await text()).length < 20) errs.push('BLANK SCREEN (body text < 20 chars)')
if (shot) await pg.screenshot({ path: shot, fullPage: true })
await b.close()
if (errs.length) { console.log('FAIL\n' + errs.join('\n')); process.exit(1) }
console.log('PASS: no page errors, no 5xx, screen not blank')
