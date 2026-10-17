import { fmtDateFull } from './time.js'

// Normalises the plan_* fields of GET /api/user (with a fallback to legacy fields).
export function getPlan(user) {
  if (!user) return null
  const unlimited = user.searches_left === -1
  let kind = user.plan_kind
  if (!kind) {
    kind = user.is_admin ? 'admin' : unlimited ? 'premium' : user.is_subscriber ? 'searches' : 'free'
  }
  const names = {
    admin: 'מנהל · גישה מלאה', premium: 'מסלול Premium', permanent: 'מסלול Premium קבוע',
    searches: 'חבילת חיפושים', free: 'מסלול חינמי',
  }
  const daysLeft = Number.isFinite(user.plan_days_left) ? user.plan_days_left : null
  const expires = kind === 'premium' ? (user.plan_expires || null) : null
  return {
    kind,
    name: user.plan_name || names[kind] || names.free,
    expires,
    daysLeft,
    isUnlimited: unlimited,
    isFree: kind === 'free',
    isPremium: kind === 'premium' || kind === 'permanent' || kind === 'admin',
    // nothing to buy / extend
    isFixed: kind === 'permanent' || kind === 'admin',
    expiringSoon: kind === 'premium' && daysLeft != null && daysLeft <= 7,
  }
}

export function formatPlanExpiry(iso) {
  return iso ? fmtDateFull(iso) : ''
}

export function daysLeftLabel(n) {
  if (n == null) return ''
  if (n <= 0) return 'היום האחרון'
  if (n === 1) return 'נותר יום אחד'
  return `נותרו ${n} ימים`
}

// "בתוקף עד 12/11/2026 · נותרו 30 ימים"
export function planExpiryLine(plan) {
  if (!plan?.expires) return ''
  const parts = [`בתוקף עד ${formatPlanExpiry(plan.expires)}`]
  const d = daysLeftLabel(plan.daysLeft)
  if (d) parts.push(d)
  return parts.join(' · ')
}

export function planIcon(plan) {
  if (!plan) return '🆓'
  return plan.kind === 'admin' ? '🛡️' : plan.kind === 'free' ? '🆓' : plan.kind === 'searches' ? '🔍' : '⭐'
}

export function globalBenefit(user) {
  if (!user?.global_unlimited_active) return null
  const label = user.global_unlimited_label || 'הבוט פתוח לכולם ללא הגבלה'
  const exp = user.global_unlimited_expires ? formatPlanExpiry(user.global_unlimited_expires) : ''
  return { label, exp }
}

// Hebrew plural for months: חודש / חודשיים / N חודשים
export function monthsLabel(n) {
  if (n === 1) return 'חודש'
  if (n === 2) return 'חודשיים'
  return `${n} חודשים`
}

// New expiry (ISO) after buying `months` months: from the live expiry, otherwise from now (N x 30 days)
export function extendedExpiry(plan, months) {
  const raw = plan?.expires ? String(plan.expires).replace(' ', 'T') : ''
  const live = raw ? new Date(/Z$|[+-]\d\d:\d\d$/.test(raw) ? raw : raw + 'Z') : null
  const base = live && !isNaN(live) && live.getTime() > Date.now() ? live.getTime() : Date.now()
  return new Date(base + months * 30 * 864e5).toISOString()
}
