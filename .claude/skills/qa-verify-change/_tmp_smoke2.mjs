// Real-browser smoke test against the local API (local_api.py) serving webapp/dist.
// Usage: node smoke_ui.mjs [--path /?plate=1234567] [--allow 503] [--user 1] [--port 8099] [--shot out.png] "click text 1" "click text 2" ...
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
const startPath = opt('--path', '/')
const allow = (opt('--allow', '') || '').split(',').filter(Boolean).map(Number) // expected HTTP statuses, e.g. 503 when testing maintenance
const user = opt('--user', '1'), port = opt('--port', '8099'), shot = opt('--shot', '')
const steps = argv
const base = `http://127.0.0.1:${port}`
const initData = execFileSync('python3', ['/home/user/carinfo-bot/.claude/skills/qa-verify-change/sign_init_data.py', user]).toString().trim()

const b = await chromium.launch({ executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium', args: ['--no-sandbox'] })
const pg = await b.newPage({ viewport: { width: 390, height: 844 } }) // phone width, Telegram-like
const errs = []
pg.on('pageerror', e => errs.push('PAGEERROR ' + e.message))
pg.on('console', m => { if (m.type() === 'error' && !(allow.length && /status of (\d+)/.test(m.text()) && allow.includes(+m.text().match(/status of (\d+)/)[1])) && !/telegram\.org|ERR_TUNNEL|ERR_NAME_NOT_RESOLVED|fonts\.g/.test(m.text())) errs.push('CONSOLE ' + m.text().slice(0, 300)) })
pg.on('response', r => { if (r.url().startsWith(base) && r.status() >= 500 && !allow.includes(r.status())) errs.push(`HTTP ${r.status()} ${r.url()}`) })
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

await pg.goto(base + startPath); await pg.waitForTimeout(2000)
const text = async () => (await pg.innerText('body')).replace(/\s+/g, ' ').trim()
console.log('START :', (await text()).slice(0, 160))
const openSettings = async()=>{ await pg.getByLabel('תפריט ניהול').click(); await pg.waitForTimeout(500); await pg.getByRole('button',{name:'⚙️ הגדרות', exact:true}).click(); await pg.waitForTimeout(1500) }
for (const s of steps) {
  const loc = pg.getByText(s).last()
  if (!(await loc.count())) { errs.push(`NOT FOUND text "${s}"`); break }
  await loc.click(); await pg.waitForTimeout(2000)
  console.log(`AFTER "${s}":`, (await text()).slice(0, 160))
}

await openSettings()
const api = async () => (await (await fetch(base+'/api/admin/settings',{headers:{'X-Init-Data':initData}})).json())
const cards = pg.locator('.card', {hasText:'תזכורות טסט'})
console.log('cards found', await pg.locator('.card:has-text("תזכורות טסט")').count(), await pg.locator('.card:has-text("זיהוי מספר רכב מתמונה")').count(), await pg.locator('.card:has-text("תוצאת חיפוש כטבלה")').count())
console.log('before', (await api()).test_reminders_enabled)
await pg.locator('.card:has-text("תזכורות טסט") button.toggle').last().click(); await pg.waitForTimeout(1000)
console.log('after click api', (await api()).test_reminders_enabled, 'ui', await pg.locator('.card:has-text("תזכורות טסט")').last().innerText())
await pg.reload(); await pg.waitForTimeout(2000)
for (const s of ["אזור אישי","פאנל ניהול"]) { await pg.getByText(s).last().click(); await pg.waitForTimeout(1500) }
await openSettings()
console.log('after reload ui', (await pg.locator('.card:has-text("תזכורות טסט")').last().innerText()).replace(/\n/g,' | '))
await pg.locator('.card:has-text("תזכורות טסט") button.toggle').last().click(); await pg.waitForTimeout(800)
await pg.locator('.card:has-text("מצב תחזוקה")').last().screenshot({path:'/tmp/claude-0/maint.png'}).catch(e=>console.log('maint card shot fail'))
console.log('maint text', (await pg.locator('.card:has-text("תחזוקה")').first().innerText()).replace(/\n/g,' | '))
await pg.locator('.card:has-text("מצב תחזוקה") button.toggle').last().click(); await pg.waitForTimeout(800); console.log('maint api', (await api()).maintenance); await pg.locator('.card:has-text("מצב תחזוקה") button.toggle').last().click(); await pg.waitForTimeout(800); console.log('maint api2', (await api()).maintenance)
console.log('horizontal overflow', await pg.evaluate(()=>document.documentElement.scrollWidth - window.innerWidth))

if ((await text()).length < 20) errs.push('BLANK SCREEN (body text < 20 chars)')
if (shot) await pg.screenshot({ path: shot, fullPage: true })
await b.close()
if (errs.length) { console.log('FAIL\n' + errs.join('\n')); process.exit(1) }
console.log('PASS: no page errors, no 5xx, screen not blank')
