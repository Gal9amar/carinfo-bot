const TZ = 'Asia/Jerusalem'

// Parse a UTC timestamp string (with or without trailing Z) into a Date
function parse(ts) {
  const s = String(ts).replace(' ', 'T')
  return new Date(s.includes('+') || s.endsWith('Z') ? s : s + 'Z')
}

// Full datetime: DD/MM/YY HH:MM
export function fmtDateTime(ts) {
  if (!ts) return ''
  try {
    const d = parse(ts)
    if (isNaN(d)) return String(ts).slice(0, 16)
    return d.toLocaleString('he-IL', {
      timeZone: TZ,
      day: '2-digit', month: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  } catch { return String(ts).slice(0, 16) }
}

// Date only: DD/MM/YY
export function fmtDate(ts) {
  if (!ts) return ''
  try {
    const d = parse(ts)
    if (isNaN(d)) return String(ts).slice(0, 10)
    return d.toLocaleDateString('he-IL', {
      timeZone: TZ,
      day: '2-digit', month: '2-digit', year: '2-digit',
    })
  } catch { return String(ts).slice(0, 10) }
}

// Long date: e.g. 20 באוגוסט 2026
export function fmtDateLong(ts) {
  if (!ts) return ''
  try {
    const d = parse(ts)
    if (isNaN(d)) return String(ts).slice(0, 10)
    return d.toLocaleDateString('he-IL', {
      timeZone: TZ,
      day: 'numeric', month: 'long', year: 'numeric',
    })
  } catch { return String(ts).slice(0, 10) }
}

// Time + short date: HH:MM:SS DD/MM
export function fmtTimeShort(ts) {
  if (!ts) return ''
  try {
    const d = parse(ts)
    if (isNaN(d)) return String(ts).slice(0, 16)
    return d.toLocaleTimeString('he-IL', { timeZone: TZ, hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
           ' ' + d.toLocaleDateString('he-IL', { timeZone: TZ, day: '2-digit', month: '2-digit' })
  } catch { return String(ts).slice(0, 16) }
}

// Vehicle annual-test ("טסט") validity label, e.g. "🟢 בתוקף עד 21/08/26"
export function testStatus(tokefRaw) {
  if (!tokefRaw) return null
  try {
    const tokef = parse(tokefRaw)
    if (isNaN(tokef)) return null
    const delta = Math.floor((tokef - new Date()) / (1000 * 60 * 60 * 24))
    if (delta < 0) return `🔴 פג תוקף לפני ${Math.abs(delta)} ימים`
    if (delta <= 30) return `🟡 פג תוקף בעוד ${delta} ימים`
    return `🟢 בתוקף עד ${fmtDate(tokefRaw)}`
  } catch { return null }
}
