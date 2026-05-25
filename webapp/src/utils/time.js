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
