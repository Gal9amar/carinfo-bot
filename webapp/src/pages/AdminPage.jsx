import { useState, useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import Sheet, { Field, FieldGroup } from '../components/Sheet.jsx'
import { fmtDateTime, fmtDate as fmtDateIL, fmtTimeShort } from '../utils/time.js'
import { adminOrderApprove, adminOrderCancel, adminDeliverOrder } from '../api.js'
import {
  adminFetchStats, adminFetchUsers, adminFetchSettings,
  adminUpdateSettings, adminFetchPackages,
  adminAddPackage, adminUpdatePackage, adminDeletePackage, adminReorderPackages,
  adminFetchGrants, adminAddGrant, adminUpdateGrant, adminDeleteGrant, adminReorderGrants,
  adminGrantUser,
  adminRevokeSubscription,
  adminFetchTickets, adminFetchTicket, adminReplyTicket, adminUpdateTicketStatus,
  adminFetchPayments, adminApprovePayment, adminDeclinePayment,
  adminFetchCodes, adminCreateCode, adminDeleteCode,
  adminBroadcast, adminFetchBroadcastHistory, adminFetchScheduledBroadcasts, adminCancelScheduledBroadcast,
  adminToggleBlock,
  adminSendUserMessage,
  adminFetchUserHistory,
  adminFetchAllReferrals,
  adminFetchUserReferrals,
  adminFetchUserSentMessages,
  adminFetchPaymentMethods,
  adminAddPaymentMethod,
  adminUpdatePaymentMethod,
  adminDeletePaymentMethod,
  adminUploadLogo,
  adminFetchActivity,
  adminGiftAll,
  adminMaintenance,
  adminFetchGroups,
  adminCreateGroup,
  adminDeleteGroup,
  adminAddGroupMember,
  adminRemoveGroupMember,
  adminFetchPaypalTransactions,
  adminFetchWatches, adminCreateWatch, adminDeleteWatch, adminToggleWatch,
  adminWatchMakes, adminWatchModels, adminWatchPreview,
  adminSetWatchQuota,
  adminToggleBroadcastConsent,
  adminFetchProducts, adminAddProduct, adminUpdateProduct, adminDeleteProduct,
  adminUploadProductStock, adminFetchProductStock, adminDeleteProductStockUnit,
  adminFetchBanners, adminAddBanner, adminUpdateBanner, adminDeleteBanner, adminReorderBanners,
} from '../api.js'
import BackButton from '../components/BackButton.jsx'
import AdminItemCard, { AdminItemBtn, AdminItemConfirm } from '../components/AdminItemCard.jsx'

const TABS = [
  { id: 'stats',    icon: '📊', label: 'סטטיסטיקות' },
  { id: 'activity', icon: '🕐', label: 'לוג פעילות' },
  { id: 'payments', icon: '💳', label: 'הזמנות' },
  { id: 'packages', icon: '🛒', label: 'מוצרים' },
  { id: 'products', icon: '📦', label: 'מוצרים דיגיטליים' },
  { id: 'banners',  icon: '🖼️', label: 'באנרים' },
  { id: 'grants',   icon: '🎁', label: 'הטבות מנהל' },
  { id: 'codes',    icon: '🔑', label: 'קודים' },
  { id: 'users',     icon: '👥', label: 'משתמשים' },
  { id: 'referrals', icon: '🤝', label: 'הפניות' },
  { id: 'groups',   icon: '👥', label: 'קבוצות' },
  { id: 'features', icon: '⭐', label: 'פיצ\'רים' },
  { id: 'promo',    icon: '🎉', label: 'מבצעי הצטרפות' },
  { id: 'broadcast',icon: '📢', label: 'שידור' },
  { id: 'settings',        icon: '⚙️', label: 'הגדרות' },
  { id: 'tickets',         icon: '🎫', label: 'טיקטים' },
  { id: 'payment_methods', icon: '💰', label: 'אמצעי תשלום' },
]

export default function AdminPage({ user, onBack }) {
  const [tab, setTab] = useState('stats')
  const [menuOpen, setMenuOpen] = useState(false)
  const currentTab = TABS.find(t => t.id === tab) || TABS[0]

  return (
    <div className="page">
      {onBack && <BackButton onClick={onBack} />}
      <h1 className="page-title">🛠 פאנל ניהול</h1>
      <div style={{ position: 'relative', marginBottom: 24 }}>
        <button
          onClick={() => setMenuOpen(o => !o)}
          aria-expanded={menuOpen}
          aria-haspopup="true"
          style={{
            display: 'flex', alignItems: 'center', gap: 12, width: '100%',
            padding: '12px 16px', borderRadius: 16, cursor: 'pointer',
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            color: 'var(--text-main)', fontSize: 15, fontWeight: 700, textAlign: 'right',
          }}
        >
          <span style={{ fontSize: 22, lineHeight: 1 }} aria-hidden="true">{menuOpen ? '✕' : '☰'}</span>
          <span style={{ flex: 1 }}><span className="sr-only">תפריט ניהול: </span>{currentTab.icon} {currentTab.label}</span>
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }} aria-hidden="true">{menuOpen ? '▲' : '▼'}</span>
        </button>
        {menuOpen && (
          <div style={{
            position: 'absolute', top: 'calc(100% + 6px)', left: 0, right: 0, zIndex: 50,
            maxHeight: '60vh', overflowY: 'auto',
            background: '#fff', border: '1px solid var(--border)', borderRadius: 16,
            boxShadow: '0 12px 32px rgba(0, 50, 150, 0.18)', padding: 6,
          }}>
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => { setTab(t.id); setMenuOpen(false) }}
                aria-current={tab === t.id ? 'page' : undefined}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10, width: '100%',
                  padding: '12px 14px', borderRadius: 12, cursor: 'pointer', textAlign: 'right',
                  border: 'none', fontSize: 15,
                  background: tab === t.id ? 'rgba(0, 122, 255, 0.1)' : 'transparent',
                  color: tab === t.id ? 'var(--primary)' : 'var(--text-main)',
                  fontWeight: tab === t.id ? 700 : 500,
                }}
              >
                <span style={{ fontSize: 18 }}>{t.icon}</span>
                <span>{t.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      {tab === 'stats'    && <StatsTab onNavigate={setTab} />}
      {tab === 'activity' && <ActivityTab />}
      {tab === 'payments' && <PaymentsTab />}
      {tab === 'packages' && <PackagesTab />}
      {tab === 'products' && <ProductsTab />}
      {tab === 'banners'  && <BannersTab />}
      {tab === 'grants'   && <AdminGrantsTab />}
      {tab === 'codes'    && <CodesSection standalone />}
      {tab === 'users'     && <UsersTab />}
      {tab === 'referrals' && <ReferralsTab />}
      {tab === 'groups'    && <GroupsTab />}
      {tab === 'features'  && <FeaturesTab />}
      {tab === 'promo'     && <PromoTab />}
      {tab === 'broadcast' && <BroadcastTab />}
      {tab === 'settings'  && <SettingsTab />}
      {tab === 'tickets'         && <TicketsTab />}
      {tab === 'payment_methods' && <PaymentMethodsTab />}
      {tab === 'watches'   && <WatchesTab />}
    </div>
  )
}

// ── Statistics tab ───────────────────────────────────────────────
const fmtNum = (n) => (Number(n) || 0).toLocaleString('he-IL')
const fmtDec = (n) => (Number(n) || 0).toLocaleString('he-IL', { maximumFractionDigits: 1 })
// Guarded ratio: null when the denominator is 0/invalid (shown as "—").
const ratio = (a, b) => (Number(b) > 0 ? (Number(a) || 0) / Number(b) : null)
const pctText = (r) => (r == null ? '—' : `${fmtDec(r * 100)}%`)

function StatsMetric({ value, label, hint, unit }) {
  return (
    <div style={{ minWidth: 0, padding: '12px', borderRadius: 14, background: 'rgba(0,122,255,0.04)', border: '1px solid var(--border)' }}>
      <dt style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-main)', marginBottom: 4 }}>{label}</dt>
      <dd style={{ margin: 0, fontSize: 26, fontWeight: 900, lineHeight: 1.1, color: 'var(--text-main)', letterSpacing: '-0.5px' }}>
        <span dir="ltr" style={{ unicodeBidi: 'isolate' }}>{value}</span>
        {unit && <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', marginInlineStart: 4 }}>{unit}</span>}
      </dd>
      {hint && <dd style={{ margin: '6px 0 0', fontSize: 12, lineHeight: 1.4, color: 'var(--text-muted)' }}>{hint}</dd>}
    </div>
  )
}

function StatsSection({ id, icon, title, desc, children }) {
  return (
    <section aria-labelledby={id} className="card" style={{ padding: 16, margin: '0 0 16px' }}>
      <h2 id={id} style={{ fontSize: 17, fontWeight: 800, color: 'var(--text-main)', margin: 0 }}>
        <span aria-hidden="true">{icon} </span>{title}
      </h2>
      <p style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--text-muted)', margin: '4px 0 12px' }}>{desc}</p>
      {children}
    </section>
  )
}

const statsGrid = { display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 10, margin: 0 }

function StatsBar({ value, color = 'var(--primary)' }) {
  const pct = Math.max(0, Math.min(100, Math.round((value || 0) * 100)))
  return (
    <div aria-hidden="true" style={{ height: 8, borderRadius: 4, background: 'rgba(0,0,0,0.07)', overflow: 'hidden' }}>
      <div style={{ width: `${pct}%`, height: '100%', borderRadius: 4, background: color }} />
    </div>
  )
}

function StatsActionRow({ icon, label, count, onClick, doneText }) {
  const rowStyle = {
    display: 'flex', alignItems: 'center', gap: 10, width: '100%', minHeight: 48, boxSizing: 'border-box',
    padding: '10px 12px', borderRadius: 14, textAlign: 'start', fontSize: 15, fontFamily: 'inherit',
    color: 'var(--text-main)',
  }
  if (!count) {
    return (
      <div style={{ ...rowStyle, background: 'rgba(52,199,89,0.08)', border: '1px solid var(--border)' }}>
        <span aria-hidden="true">✅</span>
        <span style={{ flex: 1, minWidth: 0 }}>{doneText}</span>
      </div>
    )
  }
  const inner = (
    <>
      <span aria-hidden="true">{icon}</span>
      <span style={{ flex: 1, minWidth: 0, fontWeight: 700 }}>{label}</span>
      <span style={{ minWidth: 28, textAlign: 'center', padding: '2px 10px', borderRadius: 999, background: '#9a4a07', color: '#fff', fontWeight: 800, fontSize: 14 }}>
        <span dir="ltr" style={{ unicodeBidi: 'isolate' }}>{fmtNum(count)}</span>
      </span>
      {onClick && (
        <>
          <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--primary)' }}>לטיפול</span>
          <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 3 5 8l5 5" /></svg>
        </>
      )}
    </>
  )
  const style = { ...rowStyle, background: 'rgba(245,158,11,0.12)', border: '1px solid #b45309' }
  return onClick
    ? <button type="button" onClick={onClick} style={{ ...style, cursor: 'pointer' }}>{inner}</button>
    : <div style={style}>{inner}</div>
}

function StatsSkeleton() {
  return (
    <div role="status" aria-label="טוען סטטיסטיקות" aria-busy="true">
      {[0, 1, 2].map(i => (
        <div key={i} className="card" style={{ padding: 16, margin: '0 0 16px' }}>
          <div className="skeleton" style={{ height: 20, width: '45%', marginBottom: 8 }} />
          <div className="skeleton" style={{ height: 14, width: '80%', marginBottom: 14 }} />
          <div style={statsGrid}>
            {[0, 1, 2, 3].map(j => <div key={j} className="skeleton" style={{ height: 84, borderRadius: 14 }} />)}
          </div>
        </div>
      ))}
    </div>
  )
}

function StatsTab({ onNavigate }) {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(false)
  const [busy, setBusy] = useState(true)
  const [updatedAt, setUpdatedAt] = useState(null)

  function load() {
    setBusy(true); setError(false)
    adminFetchStats()
      .then(s => { setStats(s && typeof s === 'object' ? s : {}); setUpdatedAt(new Date()) })
      .catch(() => setError(true))
      .finally(() => setBusy(false))
  }
  useEffect(() => { load() }, [])

  if (!stats && busy) return <StatsSkeleton />
  if (!stats) {
    return (
      <div className="card" role="alert" style={{ padding: 24, textAlign: 'center' }}>
        <div style={{ fontSize: 32 }} aria-hidden="true">⚠️</div>
        <p style={{ fontSize: 15, fontWeight: 700, margin: '8px 0 4px' }}>לא הצלחנו לטעון את הסטטיסטיקות</p>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', margin: '0 0 16px' }}>בדקו את החיבור ונסו שוב.</p>
        <button type="button" className="btn" onClick={load}>נסו שוב</button>
      </div>
    )
  }

  const s = stats
  const n = (k) => Number(s[k]) || 0
  const time = updatedAt ? updatedAt.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit', hour12: false }) : ''
  const conv = ratio(n('subscribers'), n('total_users'))
  const perDay = n('searches_week') / 7
  const perActive = ratio(n('searches_week'), n('active_week'))
  const codesUsed = ratio(n('used_codes'), n('total_codes'))
  const top = Array.isArray(s.top_users) ? s.top_users : []
  const topMax = Math.max(1, ...top.map(u => Number(u?.searches) || 0))
  const needsAttention = n('tickets_open') + n('pending_payments') > 0

  return (
    <div className="tab-fade-in">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 16 }}>
        <p role="status" style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>
          {error ? 'הרענון נכשל, מוצגים נתונים קודמים' : <>עודכן ב-<span dir="ltr" style={{ unicodeBidi: 'isolate' }}>{time}</span></>}
        </p>
        <button type="button" className="btn-secondary" onClick={load} disabled={busy}
          style={{ minHeight: 44, padding: '0 16px', borderRadius: 12, fontSize: 14, fontWeight: 700, cursor: busy ? 'default' : 'pointer', flexShrink: 0 }}>
          <span aria-hidden="true">🔄 </span>{busy ? 'מרענן…' : 'רענון'}
        </button>
      </div>

      <StatsSection id="st-attn" icon="🛎️" title="דורש טיפול" desc="דברים שממתינים לך עכשיו. לחיצה תעביר ללשונית הרלוונטית.">
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <li><StatsActionRow icon="🎫" label="פניות פתוחות" count={n('tickets_open')} doneText="אין פניות פתוחות" onClick={onNavigate ? () => onNavigate('tickets') : undefined} /></li>
          <li><StatsActionRow icon="💳" label="תשלומים ממתינים לאישור" count={n('pending_payments')} doneText="אין תשלומים ממתינים" onClick={onNavigate ? () => onNavigate('payments') : undefined} /></li>
        </ul>
        {!needsAttention && <p style={{ margin: '10px 0 0', fontSize: 13, color: 'var(--text-muted)' }}>הכול מטופל, אין משימות פתוחות.</p>}
      </StatsSection>

      <StatsSection id="st-users" icon="👥" title="משתמשים" desc="כמה אנשים משתמשים בבוט, וכמה מהם פעילים לאחרונה.">
        <dl style={statsGrid}>
          <StatsMetric label="סה״כ משתמשים" value={fmtNum(n('total_users'))} hint="כל מי שהצטרף אי פעם" />
          <StatsMetric label="חדשים היום" value={fmtNum(n('new_today'))} hint={`${fmtNum(n('new_week'))} ב-7 הימים האחרונים`} />
          <StatsMetric label="פעילים (7 ימים)" value={fmtNum(n('active_week'))} hint="פעילים = נכנסו ב-7 הימים האחרונים" />
          <StatsMetric label="פעילים (30 יום)" value={fmtNum(n('active_month'))} hint="נכנסו ב-30 הימים האחרונים" />
          <StatsMetric label="חסומים" value={fmtNum(n('blocked_users'))} hint="משתמשים שנחסמו ולא יכולים לחפש" />
        </dl>
      </StatsSection>

      <StatsSection id="st-prem" icon="⭐" title="מנויי Premium" desc="מי משלם או נהנה ממנוי, ומה צפוי להסתיים בקרוב.">
        {n('expiring_soon') > 0 && (
          <div role="note" style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '10px 12px', marginBottom: 12, borderRadius: 14, background: 'rgba(245,158,11,0.12)', border: '1px solid #b45309', fontSize: 14, lineHeight: 1.5 }}>
            <span aria-hidden="true">⚠️</span>
            <span><strong>שימו לב:</strong> {n('expiring_soon') === 1 ? 'מסלול אחד מסתיים' : `${fmtNum(n('expiring_soon'))} מסלולים מסתיימים`} ב-7 הימים הקרובים.</span>
          </div>
        )}
        <dl style={statsGrid}>
          <StatsMetric label="מנויים פעילים" value={fmtNum(n('subscribers'))} hint="חברים בקבוצת ״מנויים״" />
          <StatsMetric label="ללא הגבלה" value={fmtNum(n('unlimited'))} hint="מסלול ללא הגבלה שעדיין בתוקף" />
          <StatsMetric label="פגים בקרוב" value={fmtNum(n('expiring_soon'))} hint="מסלולים שמסתיימים תוך 7 ימים" />
          <StatsMetric label="אחוז המרה" value={pctText(conv)} hint="מנויים מתוך כלל המשתמשים" />
        </dl>
      </StatsSection>

      <StatsSection id="st-search" icon="🔍" title="חיפושים" desc="כמה חיפושי רכב בוצעו, ובאיזה קצב.">
        <dl style={statsGrid}>
          <StatsMetric label="סה״כ חיפושים" value={fmtNum(n('total_searches'))} hint="מאז תחילת הפעילות" />
          <StatsMetric label="היום" value={fmtNum(n('searches_today'))} hint="מתחילת היום" />
          <StatsMetric label="7 ימים" value={fmtNum(n('searches_week'))} hint="בשבוע האחרון" />
          <StatsMetric label="ממוצע ליום" value={fmtDec(perDay)} hint="חיפושים ב-7 ימים חלקי 7" />
          <StatsMetric label="למשתמש פעיל" value={perActive == null ? '—' : fmtDec(perActive)} hint="חיפושי 7 ימים חלקי פעילים" />
        </dl>
      </StatsSection>

      <StatsSection id="st-watch" icon="🔔" title="התראות יד2" desc="מעקב אחרי מודעות חדשות לפי יצרן, דגם ושנה.">
        <dl style={statsGrid}>
          <StatsMetric label="התראות פעילות" value={fmtNum(n('watches_total'))} hint="מעקבים שפעילים כרגע" />
          <StatsMetric label="משתמשים עם התראה" value={fmtNum(n('watches_users'))} hint="משתמשים ייחודיים" />
          <StatsMetric label="נוספו השבוע" value={fmtNum(n('watches_week'))} hint="התראות חדשות ב-7 ימים" />
        </dl>
      </StatsSection>

      <StatsSection id="st-codes" icon="🎟️" title="קודי הטבה" desc="קודים שנוצרו, כמה מהם מומשו וכמה עדיין פנויים.">
        <dl style={statsGrid}>
          <StatsMetric label="סה״כ קודים" value={fmtNum(n('total_codes'))} hint="כל הקודים שנוצרו" />
          <StatsMetric label="נוצלו" value={fmtNum(n('used_codes'))} hint="קודים שמישהו מימש" />
          <StatsMetric label="פעילים" value={fmtNum(n('active_codes'))} hint="לא נוצלו ולא פגו" />
        </dl>
        <div style={{ marginTop: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6, color: 'var(--text-main)' }}>
            <span>ניצול קודים</span>
            <span dir="ltr" style={{ unicodeBidi: 'isolate', fontWeight: 700 }}>{fmtNum(n('used_codes'))} / {fmtNum(n('total_codes'))} ({pctText(codesUsed)})</span>
          </div>
          <StatsBar value={codesUsed} />
        </div>
      </StatsSection>

      <StatsSection id="st-top" icon="🏆" title="משתמשים מובילים" desc="חמשת המשתמשים עם הכי הרבה חיפושים מאז ההצטרפות.">
        {top.length === 0 ? (
          <p style={{ margin: 0, fontSize: 14, color: 'var(--text-muted)', textAlign: 'center', padding: '8px 0' }}>עדיין אין חיפושים להצגה.</p>
        ) : (
          <ol style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {top.map((u, i) => {
              const cnt = Number(u?.searches) || 0
              return (
                <li key={i} style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <span aria-hidden="true" style={{ width: 28, height: 28, borderRadius: '50%', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 800, background: i === 0 ? '#92400e' : 'rgba(0,122,255,0.1)', color: i === 0 ? '#fff' : 'var(--primary)' }}>{i + 1}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: 14, marginBottom: 4 }}>
                      <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', unicodeBidi: 'plaintext', fontWeight: 600 }}>
                        <span className="sr-only">מקום {i + 1}: </span>{u?.name || 'ללא שם'}
                      </span>
                      <span style={{ flexShrink: 0, fontWeight: 800 }}><span dir="ltr" style={{ unicodeBidi: 'isolate' }}>{fmtNum(cnt)}</span> <span style={{ fontWeight: 500, color: 'var(--text-muted)', fontSize: 12 }}>חיפושים</span></span>
                    </div>
                    <StatsBar value={cnt / topMax} />
                  </div>
                </li>
              )
            })}
          </ol>
        )}
      </StatsSection>
    </div>
  )
}

function ActivityTab() {
  const [log, setLog] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  function load() { adminFetchActivity(100).then(setLog).catch(() => {}) }
  useEffect(() => { load() }, [])
  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [autoRefresh])

  function fmtTime(ts) { return fmtTimeShort(ts) }

  return (
    <div className="tab-fade-in">
      <div className="card" style={{ padding: '20px', marginBottom: 24, background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.05), transparent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 24 }}>⚡</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>יומן פעילות מערכת</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>{log ? `מציג את ${log.length} הפעולות האחרונות בזמן אמת` : 'טוען נתונים...'}</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', background: 'var(--bg-card)', padding: '8px 16px', borderRadius: 12, border: '1px solid var(--border)' }}>
          <div style={{ width: 18, height: 18, borderRadius: 6, border: `2px solid ${autoRefresh ? '#047857' : 'var(--border)'}`, background: autoRefresh ? '#047857' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {autoRefresh && <span style={{ color: '#fff', fontSize: 10 }}>✓</span>}
          </div>
          <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} style={{ display: 'none' }} />
          <span style={{ fontSize: 13, fontWeight: 700, color: autoRefresh ? 'var(--text-main)' : 'var(--text-muted)' }}>רענון חיטוב אוטומטי (15 ש')</span>
          {autoRefresh && (
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#047857', marginLeft: 4, animation: 'pulse 2s infinite' }}></div>
          )}
        </label>
        
        <button
          onClick={load}
          style={{ width: 38, height: 38, borderRadius: 12, background: 'var(--bg-card)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', fontSize: 16, color: 'var(--text-main)', transition: 'all 0.2s' }}
          title="רענן עכשיו"
        >🔄</button>
      </div>

      {!log && <div className="loading"></div>}
      
      {log && log.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40, background: 'var(--bg-card)', borderRadius: 16, border: '1px dashed var(--border)', color: 'var(--hint)', fontSize: 14 }}>
          טרם נרשמו פעולות במערכת
        </div>
      )}
      
      {log && log.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {log.map((item, i) => (
            <div key={item.id} style={{
              display: 'flex', gap: 16, alignItems: 'center', padding: '16px',
              borderBottom: i < log.length - 1 ? '1px solid var(--border)' : 'none',
              background: i % 2 === 0 ? 'transparent' : 'rgba(0,100,200,0.03)',
              transition: 'background 0.2s'
            }}>
              <div style={{ width: 44, height: 44, borderRadius: 12, background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, flexShrink: 0, border: '1px solid var(--border)' }}>
                {item.icon}
              </div>
              
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-main)', marginBottom: 4, wordBreak: 'break-word', lineHeight: 1.4 }}>
                  {item.description}
                </div>
                {item.username && (
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ color: 'var(--primary)' }}>👤</span> {item.username}
                  </div>
                )}
              </div>
              
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', background: 'var(--bg)', padding: '6px 10px', borderRadius: 8, whiteSpace: 'nowrap' }}>
                {fmtTime(item.created_at)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Same lines as PLAN_FEATURES in PackagesPage.jsx / src/packages.py
const DEFAULT_PKG_FEATURES = [
  'נתוני רכב מלאים — שנה, דגם, בעלות, טסט, ק״מ',
  'היסטוריית חיפושים אישית',
  'השוואת רכבים',
  'תזכורת טסט וניהול ״רכבים שקניתי״',
  'חיפושים ללא הגבלה',
  'מחיר שוק Yad2',
  'התראות על מודעות חדשות ב-Yad2',
  'דוח PDF מפורט',
  'גישה לכל פיצ׳רי הפרימיום העתידיים',
]

// Normalize features array — handles both old string[] and new {text,included}[] formats
function normalizeFeatures(raw) {
  if (!raw || !raw.length) return DEFAULT_PKG_FEATURES.map(text => ({ text, included: true }))
  return raw.map(item => typeof item === 'string' ? { text: item, included: true } : item)
}

// Generate chips that PackagesPage auto-displays when a package has no chips saved
function getDefaultChips(pkg) {
  const s = typeof pkg.searches === 'number' ? pkg.searches : parseInt(pkg.searches)
  const duration = typeof pkg.duration_months === 'number' ? pkg.duration_months : parseInt(pkg.duration_months) || 1
  if (s === 0)  return ['🔍 חיפושים בהצטרפות', '🤝 +חיפושים על הפניות', '🔓 ללא תפוגה']
  if (s === -1) return ['♾️ ללא הגבלה', '💳 חד-פעמי', `📅 תוקף ${duration > 1 ? `${duration} חודשים` : 'חודש'}`]
  return [`🔍 ${s} חיפושים`, '💳 חד-פעמי', '🔓 ללא תפוגה']
}

function PackagesTab() {
  const [pkgs, setPkgs] = useState(null)
  const [editing, setEditing] = useState(null)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ label: '', searches: '', price: '', image_url: '', features: normalizeFeatures([]), chips: [] })
  const [saving, setSaving] = useState(false)
  const [dragIdx, setDragIdx] = useState(null)
  const [reordering, setReordering] = useState(false)
  const [confirmId, setConfirmId] = useState(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => { adminFetchPackages().then(setPkgs).catch(() => {}) }, [])

  async function applyReorder(nextPaid) {
    // keep the free card in pkgs but reorder only paid packages
    setPkgs(prev => {
      const free = prev.filter(p => p.searches === 0)
      return [...free, ...nextPaid]
    })
    setReordering(true)
    try {
      const fresh = await adminReorderPackages(nextPaid.map(p => p.id))
      setPkgs(fresh)
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה בעדכון הסדר')
      setPkgs(await adminFetchPackages())
    }
    setReordering(false)
  }

  function movePackage(fromIdx, toIdx) {
    if (!pkgs) return
    const paid = pkgs.filter(p => p.searches !== 0)
    if (fromIdx === toIdx || fromIdx < 0 || toIdx < 0 || fromIdx >= paid.length || toIdx >= paid.length) return
    const next = [...paid]
    const [moved] = next.splice(fromIdx, 1)
    next.splice(toIdx, 0, moved)
    applyReorder(next)
  }

  async function saveEdit() {
    setSaving(true)
    try {
      await adminUpdatePackage(editing.id, {
        label: form.label,
        searches: parseInt(form.searches),
        price: parseInt(form.price),
        image_url: form.image_url || '',
        duration_months: parseInt(form.duration_months) || 1,
        features: form.features || [],
        chips: form.chips || [],
        package_type: form.package_type || 'searches',
        is_active: form.is_active !== false,
      })
      const fresh = await adminFetchPackages()
      setPkgs(fresh)
      setEditing(null)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function saveAdd() {
    setSaving(true)
    try {
      const fresh = await adminAddPackage({
        label: form.label,
        searches: parseInt(form.searches),
        price: parseInt(form.price),
        image_url: form.image_url || '',
        duration_months: parseInt(form.duration_months) || 1,
        features: form.features || [],
        chips: form.chips || [],
        package_type: form.package_type || 'searches',
        is_active: form.is_active !== false,
      })
      setPkgs(fresh)
      setAdding(false)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function deletePkg(id) {
    // confirmation is the inline step on the card (confirmId)
    setDeleting(true)
    try {
      await adminDeletePackage(id)
      setPkgs(await adminFetchPackages())
      setConfirmId(null)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה במחיקת המוצר') }
    setDeleting(false)
  }

  if (!pkgs) return <div className="loading"></div>

  const freePkg  = pkgs.find(p => p.searches === 0)
  const paidPkgs = pkgs.filter(p => p.searches !== 0)
  const allChipsPool = [...new Set(pkgs.flatMap(p => p.chips || []))]

  return (
    <div>
      {/* FREE card row */}
      {freePkg && (
        <div style={{
          background: 'linear-gradient(135deg,#1b433218,#2d6a4f18)',
          border: '1.5px solid #52b78840',
          borderRadius: 14, padding: '10px 14px', marginBottom: 14,
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span style={{ fontSize: 22, flexShrink: 0 }}>🆓</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 14, color: '#52b788' }}>{freePkg.label}</div>
            <div style={{ fontSize: 12, color: 'var(--hint)' }}>כרטיס FREE · {freePkg.features?.length ?? 0} תכונות</div>
          </div>
          <button
            className="btn"
            style={{ width: 'auto', padding: '6px 14px', marginTop: 0, fontSize: 13 }}
            onClick={() => { setEditing(freePkg); setForm({ label: freePkg.label, searches: '0', price: '0', image_url: freePkg.image_url || '', duration_months: '1', features: normalizeFeatures(freePkg.features), chips: freePkg.chips?.length ? freePkg.chips : getDefaultChips(freePkg), package_type: freePkg.package_type || 'searches' }) }}
          >✏️ ערוך</button>
        </div>
      )}

      <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 10 }}>
        סדר התצוגה: גרור כרטיס או השתמש בחצים · 1 = ראשון
      </div>
      <div className="admin-item-list" style={{ marginBottom: 16 }}>
      {paidPkgs.map((pkg, idx) => {
        const desc = pkg.searches === -1 ? 'חיפושים ללא הגבלה (Premium)' : `${pkg.searches} חיפושים`
        const isDragging = dragIdx === idx
        const isActive = pkg.is_active !== false
        return (
          <AdminItemCard
            key={pkg.id}
            draggable={!reordering}
            onDragStart={() => setDragIdx(idx)}
            onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move' }}
            onDrop={() => { if (dragIdx !== null) movePackage(dragIdx, idx); setDragIdx(null) }}
            onDragEnd={() => setDragIdx(null)}
            className={isDragging ? 'dragging' : ''}
            style={{ opacity: isDragging ? 0.45 : isActive ? 1 : 0.65, cursor: reordering ? 'wait' : 'grab' }}
            leading={<span aria-label={`מספר ${idx + 1}`}>{idx + 1}</span>}
            title={pkg.label}
            badge={<bdi dir="ltr">₪{pkg.price}</bdi>}
            badgeTone="good"
            subtitle={desc}
            meta={!isActive ? <span className="admin-item-badge mute">מושבת</span> : null}
            actions={<>
              <AdminItemBtn icon="▲" label="למעלה" ariaLabel={`הזז למעלה: ${pkg.label}`} disabled={idx === 0 || reordering} onClick={() => movePackage(idx, idx - 1)} />
              <AdminItemBtn icon="▼" label="למטה" ariaLabel={`הזז למטה: ${pkg.label}`} disabled={idx === paidPkgs.length - 1 || reordering} onClick={() => movePackage(idx, idx + 1)} />
              <AdminItemBtn icon="✏️" label="ערוך" ariaLabel={`ערוך מוצר: ${pkg.label}`} onClick={() => { setEditing(pkg); setForm({ label: pkg.label, searches: String(pkg.searches), price: String(pkg.price), image_url: pkg.image_url || '', duration_months: String(pkg.duration_months ?? 1), features: normalizeFeatures(pkg.features), chips: pkg.chips?.length ? pkg.chips : getDefaultChips(pkg), is_active: pkg.is_active !== false, package_type: pkg.package_type || 'searches' }) }} />
              <AdminItemBtn icon="🗑️" label="מחק" ariaLabel={`מחק מוצר: ${pkg.label}`} danger onClick={() => setConfirmId(pkg.id)} />
            </>}
            footer={confirmId === pkg.id && (
              <AdminItemConfirm text="למחוק את המוצר? אי אפשר לבטל." busy={deleting}
                onYes={() => deletePkg(pkg.id)} onNo={() => setConfirmId(null)} />
            )}
          />
        )
      })}
      </div>
      <button className="btn btn-success" onClick={() => { setAdding(true); setForm({ label: '', searches: '', price: '', image_url: '', duration_months: '1', features: normalizeFeatures([]), chips: [], is_active: true }) }}>
        ➕ הוסף מוצר
      </button>

      {editing && (
        <PackageModal
          title="✏️ עריכת מוצר"
          form={form} setForm={setForm}
          saving={saving} onSave={saveEdit} onClose={() => setEditing(null)}
          suggestions={allChipsPool}
        />
      )}
      {adding && (
        <PackageModal
          title="➕ מוצר חדש"
          form={form} setForm={setForm}
          saving={saving} onSave={saveAdd} onClose={() => setAdding(false)}
          suggestions={allChipsPool}
        />
      )}
    </div>
  )
}

function ProductsTab() {
  const [prods, setProds] = useState(null)
  const [editing, setEditing] = useState(null)
  const [adding, setAdding] = useState(false)
  const [stockTarget, setStockTarget] = useState(null)
  const [form, setForm] = useState({ name: '', description: '', image_url: '', price: '', delivery_type: 'manual', delivery_time_note: '', quantity_stock: '', is_active: true, availability_status: 'available', features: [] })
  const [saving, setSaving] = useState(false)
  const [confirmId, setConfirmId] = useState(null)
  const [deleting, setDeleting] = useState(false)

  function load() { adminFetchProducts().then(setProds).catch(() => setProds([])) }
  useEffect(() => { load() }, [])

  function toBody(f) {
    return {
      name: f.name,
      description: f.description || '',
      image_url: f.image_url || '',
      price: parseInt(f.price) || 0,
      delivery_type: f.delivery_type || 'manual',
      delivery_time_note: f.delivery_time_note || '',
      quantity_stock: parseInt(f.quantity_stock) || 0,
      is_active: f.is_active !== false,
      availability_status: f.availability_status || 'available',
      features: f.features || [],
    }
  }

  async function saveEdit() {
    setSaving(true)
    try {
      await adminUpdateProduct(editing.id, toBody(form))
      load()
      setEditing(null)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function saveAdd() {
    setSaving(true)
    try {
      const res = await adminAddProduct(toBody(form))
      const lines = (form.stock_text || '').split('\n').map(l => l.trim()).filter(Boolean)
      if (form.delivery_type === 'auto' && lines.length && res?.id) {
        await adminUploadProductStock(res.id, form.stock_text)
      }
      load()
      setAdding(false)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function deleteProd(id) {
    // confirmation is the inline step on the card (confirmId)
    setDeleting(true)
    try {
      await adminDeleteProduct(id)
      load()
      setConfirmId(null)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה במחיקת המוצר') }
    setDeleting(false)
  }

  if (!prods) return <div className="loading"></div>

  return (
    <div>
      {prods.length === 0 && (
        <div style={{ color: 'var(--hint)', textAlign: 'center', padding: 24 }}>אין מוצרים דיגיטליים עדיין</div>
      )}
      <div className="admin-item-list" style={{ marginBottom: 16 }}>
      {prods.map(p => {
        const isActive = p.is_active !== false
        const deliveryLabel = p.delivery_type === 'auto' ? 'אוטומטי' : 'ידני'
        const isAuto = p.delivery_type === 'auto'
        return (
          <AdminItemCard
            key={p.id}
            style={{ opacity: isActive ? 1 : 0.7 }}
            title={p.name}
            badge={<bdi dir="ltr">₪{p.price}</bdi>}
            badgeTone="good"
            subtitle={`משלוח ${deliveryLabel} · מלאי: ${p.stock_count ?? 0}${p.delivery_time_note ? ` · ⏱ ${p.delivery_time_note}` : ''}`}
            meta={(p.availability_status === 'coming_soon' || !isActive) ? <>
              {p.availability_status === 'coming_soon' && <span className="admin-item-badge">🔜 בקרוב</span>}
              {!isActive && <span className="admin-item-badge mute">מושבת</span>}
            </> : null}
            cols={isAuto ? 3 : 2}
            actions={<>
              <AdminItemBtn icon="✏️" label="ערוך" ariaLabel={`ערוך מוצר: ${p.name}`} onClick={() => { setEditing(p); setForm({ name: p.name, description: p.description || '', image_url: p.image_url || '', price: String(p.price), delivery_type: p.delivery_type, delivery_time_note: p.delivery_time_note || '', quantity_stock: String(p.quantity_stock ?? 0), is_active: p.is_active !== false, availability_status: p.availability_status || 'available', features: p.features || [] }) }} />
              {isAuto && <AdminItemBtn icon="📤" label="מלאי" ariaLabel={`ניהול מלאי: ${p.name}`} onClick={() => setStockTarget(p)} />}
              <AdminItemBtn icon="🗑️" label="מחק" ariaLabel={`מחק מוצר: ${p.name}`} danger onClick={() => setConfirmId(p.id)} />
            </>}
            footer={confirmId === p.id && (
              <AdminItemConfirm text="למחוק את המוצר? אי אפשר לבטל." busy={deleting}
                onYes={() => deleteProd(p.id)} onNo={() => setConfirmId(null)} />
            )}
          />
        )
      })}
      </div>
      <button className="btn btn-success" onClick={() => { setAdding(true); setForm({ name: '', description: '', image_url: '', price: '', delivery_type: 'manual', delivery_time_note: '', quantity_stock: '', stock_text: '', is_active: true, availability_status: 'available', features: [] }) }}>
        ➕ הוסף מוצר דיגיטלי
      </button>

      {editing && (
        <ProductModal title="✏️ עריכת מוצר" form={form} setForm={setForm} saving={saving} onSave={saveEdit} onClose={() => setEditing(null)} />
      )}
      {adding && (
        <ProductModal title="➕ מוצר דיגיטלי חדש" form={form} setForm={setForm} saving={saving} onSave={saveAdd} onClose={() => setAdding(false)} isNew />
      )}
      {stockTarget && (
        <ProductStockModal product={stockTarget} onClose={() => { setStockTarget(null); load() }} />
      )}
    </div>
  )
}

const BANNER_PAGE_OPTIONS = [
  { value: 'packages',   label: '🛒 החנות' },
  { value: 'orders',     label: '📦 הזמנות שלי' },
  { value: 'history',    label: '📋 חיפושים שלי' },
  { value: 'referral',   label: '🤝 הפנה חבר' },
  { value: 'ticket',     label: '🎫 תמיכה' },
  { value: 'howItWorks', label: 'ℹ️ איך זה עובד' },
  { value: 'privacy',    label: '🔒 פרטיות' },
  { value: 'watches',    label: '🔔 התראות יד2' },
]

// Where a banner can be displayed on the site
const PLACEMENT_OPTIONS = [
  { value: 'home',       label: '🏠 עמוד הבית' },
  { value: 'packages',   label: '🛒 החנות' },
  { value: 'report',     label: '📋 דוח רכב מלא' },
  { value: 'history',    label: '📜 היסטוריית חיפושים' },
  { value: 'referral',   label: '🤝 הפנה חבר' },
  { value: 'ticket',     label: '🎫 תמיכה' },
  { value: 'howItWorks', label: 'ℹ️ איך זה עובד' },
  { value: 'privacy',    label: '🔒 פרטיות' },
  { value: 'orders',     label: '📦 הזמנות שלי' },
  { value: 'watches',    label: '🔔 התראות יד2' },
]

function BannersTab() {
  const [banners, setBanners] = useState(null)
  const [editing, setEditing] = useState(null)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState(null)
  const [saving, setSaving] = useState(false)
  const [dragIdx, setDragIdx] = useState(null)
  const [reordering, setReordering] = useState(false)
  const [confirmDelId, setConfirmDelId] = useState(null)
  const [busyId, setBusyId] = useState(null)

  function load() { adminFetchBanners().then(setBanners).catch(() => setBanners([])) }
  useEffect(() => { load() }, [])

  function blankForm() {
    return { title: '', subtitle: '', icon: '🎁', image_url: '', color_from: '#177a33', color_to: '#276749', link_type: 'page', link_value: 'packages', placements: ['home'], is_active: true }
  }

  async function applyReorder(next) {
    setBanners(next)
    setReordering(true)
    try {
      setBanners(await adminReorderBanners(next.map(b => b.id)))
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה בעדכון הסדר')
      load()
    }
    setReordering(false)
  }

  function moveBanner(fromIdx, toIdx) {
    if (!banners) return
    if (fromIdx === toIdx || fromIdx < 0 || toIdx < 0 || fromIdx >= banners.length || toIdx >= banners.length) return
    const next = [...banners]
    const [moved] = next.splice(fromIdx, 1)
    next.splice(toIdx, 0, moved)
    applyReorder(next)
  }

  function toBody(f) {
    return {
      title: f.title, subtitle: f.subtitle || '', icon: f.icon || '🎁', image_url: f.image_url || '',
      color_from: f.color_from || '#177a33', color_to: f.color_to || '#276749',
      link_type: f.link_type || 'page', link_value: f.link_value || 'packages',
      placements: f.placements?.length ? f.placements : ['home'],
      is_active: f.is_active !== false,
    }
  }

  async function saveEdit() {
    setSaving(true)
    try {
      await adminUpdateBanner(editing.id, toBody(form))
      load()
      setEditing(null)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function saveAdd() {
    setSaving(true)
    try {
      await adminAddBanner(toBody(form))
      load()
      setAdding(false)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  // Confirmation is inline in the card (confirmDelId) before this runs.
  async function deleteBanner(id) {
    setBusyId(id)
    try {
      await adminDeleteBanner(id)
      setConfirmDelId(null)
      load()
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה במחיקה') }
    setBusyId(null)
  }

  async function toggleBanner(b) {
    setBusyId(b.id)
    try {
      await adminUpdateBanner(b.id, toBody({ ...b, is_active: b.is_active === false }))
      load()
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה בעדכון') }
    setBusyId(null)
  }

  if (!banners) return <div className="loading"></div>

  return (
    <div>
      <p style={{ fontSize: 13, lineHeight: 1.45, color: '#566070', margin: '0 0 12px' }}>
        באנרים אלו מוצגים בעמוד הבית של המיני-אפ. לשינוי סדר התצוגה גררו את ⠿ או השתמשו בכפתורי למעלה / למטה.
      </p>
      {banners.length === 0 && (
        <div style={{ color: '#566070', textAlign: 'center', padding: 24 }}>אין באנרים עדיין. אפשר להוסיף את הראשון למטה.</div>
      )}
      {banners.map((b, idx) => {
        const isActive = b.is_active !== false
        const isDragging = dragIdx === idx
        const busy = busyId === b.id
        const linkLabel = b.link_type === 'product'
          ? `מוצר #${b.link_value}`
          : (BANNER_PAGE_OPTIONS.find(o => o.value === b.link_value)?.label || b.link_value)
        const placements = Array.isArray(b.placements) && b.placements.length ? b.placements : ['home']
        return (
          <div
            key={b.id}
            draggable={!reordering}
            onDragStart={() => setDragIdx(idx)}
            onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move' }}
            onDrop={() => { if (dragIdx !== null) moveBanner(dragIdx, idx); setDragIdx(null) }}
            onDragEnd={() => setDragIdx(null)}
            className={`card bn-card${isActive ? '' : ' bn-off'}`}
            style={{ opacity: isDragging ? 0.45 : 1, cursor: reordering ? 'wait' : undefined }}
          >
            <div className="bn-head">
              <span className="bn-handle" aria-hidden="true" title="גרור לשינוי סדר">⠿</span>
              <div className="bn-tile" style={{ background: `linear-gradient(135deg, ${b.color_from}, ${b.color_to})` }} aria-hidden="true">
                {b.image_url ? <img src={b.image_url} alt="" width="52" height="52" /> : b.icon}
              </div>
              <div className="bn-text">
                <span className={`bn-badge ${isActive ? 'on' : 'off'}`}>{isActive ? '✓ פעיל' : '⏸ מושבת'}</span>
                <div className="bn-title">{b.title}</div>
                {b.subtitle ? <p className="bn-sub">{b.subtitle}</p> : null}
              </div>
            </div>

            <div className="bn-meta">
              <span className="bn-chip link">🔗 {linkLabel}</span>
              {placements.map(p => (
                <span key={p} className="bn-chip">{PLACEMENT_OPTIONS.find(o => o.value === p)?.label || p}</span>
              ))}
            </div>

            {confirmDelId === b.id ? (
              <div className="bn-confirm" role="alertdialog" aria-label="אישור מחיקה">
                <p>למחוק את הבאנר «{b.title}»? אי אפשר לשחזר.</p>
                <div className="row">
                  <button type="button" className="bn-btn" disabled={busy} onClick={() => setConfirmDelId(null)}>ביטול</button>
                  <button type="button" className="bn-btn yes" disabled={busy} onClick={() => deleteBanner(b.id)}>{busy ? 'מוחק…' : 'כן, מחק'}</button>
                </div>
              </div>
            ) : (
              <div className="bn-actions">
                <div className="bn-move">
                  <button type="button" className="bn-btn" aria-label="הזז למעלה" disabled={idx === 0 || reordering} onClick={() => moveBanner(idx, idx - 1)}><span className="ico" aria-hidden="true">▲</span>למעלה</button>
                  <button type="button" className="bn-btn" aria-label="הזז למטה" disabled={idx === banners.length - 1 || reordering} onClick={() => moveBanner(idx, idx + 1)}><span className="ico" aria-hidden="true">▼</span>למטה</button>
                </div>
                <button type="button" className="bn-btn" disabled={busy} aria-label={isActive ? 'הסתר באנר' : 'הצג באנר'} onClick={() => toggleBanner(b)}><span className="ico" aria-hidden="true">{isActive ? '🙈' : '👁️'}</span>{isActive ? 'הסתר' : 'הצג'}</button>
                <button type="button" className="bn-btn" aria-label="ערוך באנר" onClick={() => { setEditing(b); setForm({ title: b.title, subtitle: b.subtitle || '', icon: b.icon, image_url: b.image_url || '', color_from: b.color_from, color_to: b.color_to, link_type: b.link_type, link_value: b.link_value, placements: b.placements || ['home'], is_active: b.is_active !== false }) }}><span className="ico" aria-hidden="true">✏️</span>ערוך</button>
                <button type="button" className="bn-btn del" aria-label="מחק באנר" onClick={() => setConfirmDelId(b.id)}><span className="ico" aria-hidden="true">🗑️</span>מחק</button>
              </div>
            )}
          </div>
        )
      })}
      <button className="btn btn-success" onClick={() => { setAdding(true); setForm(blankForm()) }}>
        ➕ הוסף באנר
      </button>

      {editing && (
        <BannerModal title="✏️ עריכת באנר" form={form} setForm={setForm} saving={saving} onSave={saveEdit} onClose={() => setEditing(null)} />
      )}
      {adding && (
        <BannerModal title="➕ באנר חדש" form={form} setForm={setForm} saving={saving} onSave={saveAdd} onClose={() => setAdding(false)} />
      )}
    </div>
  )
}

function BannerModal({ title, form, setForm, saving, onSave, onClose }) {
  const fileRef = useRef(null)
  const [compressing, setCompressing] = useState(false)
  const [products, setProducts] = useState(null)

  useEffect(() => {
    if (form.link_type === 'product' && products === null) {
      adminFetchProducts().then(setProducts).catch(() => setProducts([]))
    }
  }, [form.link_type])

  function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setCompressing(true)
    const reader = new FileReader()
    reader.onload = ev => {
      const img = new Image()
      img.onload = () => {
        const MAX = 800
        const ratio = Math.min(MAX / img.width, MAX / img.height, 1)
        const canvas = document.createElement('canvas')
        canvas.width  = Math.round(img.width  * ratio)
        canvas.height = Math.round(img.height * ratio)
        canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
        setForm(f => ({ ...f, image_url: canvas.toDataURL('image/jpeg', 0.82) }))
        setCompressing(false)
      }
      img.src = ev.target.result
    }
    reader.readAsDataURL(file)
  }

  const valid = form.title?.trim() && form.link_value?.toString().trim()

  return (
    <Sheet title={title} onClose={onClose} footer={<>
      <button className="btn" disabled={saving || !valid} onClick={onSave}>{saving ? '...' : 'שמור'}</button>
      <button className="btn btn-secondary" onClick={onClose}>ביטול</button>
    </>}>
      <div>
        {/* Live preview */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 14, width: '100%',
          background: form.image_url
            ? `linear-gradient(135deg, ${form.color_from}cc 0%, ${form.color_to}cc 100%), url(${form.image_url}) center/cover`
            : `linear-gradient(135deg, ${form.color_from} 0%, ${form.color_to} 100%)`,
          border: 'none', borderRadius: 16, padding: '14px 18px', marginBottom: 16,
        }}>
          <span style={{ fontSize: 34, flexShrink: 0 }}>{form.icon || '🎁'}</span>
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: 15, marginBottom: 2 }}>{form.title || 'כותרת הבאנר'}</div>
            {form.subtitle && <div style={{ color: 'rgba(255,255,255,0.82)', fontSize: 12 }}>{form.subtitle}</div>}
          </div>
        </div>

        <Field label="כותרת"><input className="input" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} /></Field>
        <Field label="כותרת משנה"><input className="input" value={form.subtitle} onChange={e => setForm(f => ({ ...f, subtitle: e.target.value }))} /></Field>
        <Field label="אייקון (אימוג'י)"><input className="input" value={form.icon} onChange={e => setForm(f => ({ ...f, icon: e.target.value }))} /></Field>

        <div style={{ display: 'flex', gap: 10 }}>
          <Field label="צבע התחלה" style={{ flex: 1 }}>
            <input className="input" type="color" value={form.color_from} onChange={e => setForm(f => ({ ...f, color_from: e.target.value }))}
              style={{ width: '100%', height: 48, cursor: 'pointer' }} />
          </Field>
          <Field label="צבע סיום" style={{ flex: 1 }}>
            <input className="input" type="color" value={form.color_to} onChange={e => setForm(f => ({ ...f, color_to: e.target.value }))}
              style={{ width: '100%', height: 48, cursor: 'pointer' }} />
          </Field>
        </div>

        <button
          type="button" role="switch" aria-checked={form.is_active !== false}
          onClick={() => setForm(f => ({ ...f, is_active: f.is_active === false }))}
          style={{
            display: 'flex', alignItems: 'center', gap: 10, width: '100%', textAlign: 'start', fontFamily: 'inherit',
            background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 12, padding: '10px 14px', marginBottom: 14,
            minHeight: 56, cursor: 'pointer', userSelect: 'none', color: 'var(--text-main)',
          }}
        >
          <span style={{ flex: 1, minWidth: 0 }}>
            <span style={{ display: 'block', fontSize: 14, fontWeight: 700 }}>הצג באתר</span>
            <span style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              {form.is_active !== false ? 'מוצג' : 'מוסתר — לא מוצג בשום מקום'}
            </span>
          </span>
          <span aria-hidden="true" style={{
            width: 44, height: 24, borderRadius: 12, flexShrink: 0,
            background: form.is_active !== false ? '#177a33' : 'rgba(0,100,200,0.18)',
            position: 'relative', transition: 'background 0.2s',
          }}>
            <span style={{
              position: 'absolute', top: 3, width: 18, height: 18, borderRadius: '50%',
              background: '#fff', transition: 'left 0.2s',
              left: form.is_active !== false ? 23 : 3,
            }} />
          </span>
        </button>

        <FieldGroup label="באילו עמודים להציג" hint="ניתן לבחור כמה שרוצים">
        <div className="sheet-chips">
          {PLACEMENT_OPTIONS.map(o => {
            const active = (form.placements || ['home']).includes(o.value)
            return (
              <button
                key={o.value}
                type="button"
                onClick={() => setForm(f => {
                  const cur = f.placements?.length ? f.placements : ['home']
                  const next = cur.includes(o.value) ? cur.filter(p => p !== o.value) : [...cur, o.value]
                  return { ...f, placements: next }
                })}
                style={{
                  fontSize: 13, fontWeight: 600, padding: '6px 14px', borderRadius: 22, minHeight: 44, fontFamily: 'inherit',
                  border: `1.5px solid ${active ? 'var(--btn)' : 'rgba(0,100,200,0.18)'}`,
                  background: active ? 'var(--btn)22' : 'transparent',
                  color: active ? 'var(--text-main)' : 'var(--text-muted)', cursor: 'pointer',
                }}
                aria-pressed={active}
              >{active ? '✓ ' : ''}{o.label}</button>
            )
          })}
        </div>
        </FieldGroup>

        <Field label="לאן להפנות בלחיצה">
        <select
          className="input"
          value={form.link_type}
          onChange={e => {
            const link_type = e.target.value
            setForm(f => ({ ...f, link_type, link_value: link_type === 'page' ? 'packages' : '' }))
          }}
        >
          <option value="page">📄 מסך / תפריט באתר</option>
          <option value="product">📦 מוצר דיגיטלי</option>
        </select>
        </Field>

        {form.link_type === 'page' && (
          <Field label="מסך יעד">
          <select className="input" value={form.link_value} onChange={e => setForm(f => ({ ...f, link_value: e.target.value }))}>
            {BANNER_PAGE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          </Field>
        )}

        {form.link_type === 'product' && (
          products === null ? (
            <div className="field-hint" role="status" style={{ marginBottom: 14 }}>טוען מוצרים...</div>
          ) : products.length === 0 ? (
            <div className="field-hint" style={{ marginBottom: 14 }}>אין מוצרים דיגיטליים — הוסף מוצר בטאב "מוצרים דיגיטליים" קודם</div>
          ) : (
            <Field label="מוצר יעד">
            <select className="input" value={form.link_value} onChange={e => setForm(f => ({ ...f, link_value: e.target.value }))}>
              <option value="">— בחר מוצר —</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.name} · ₪{p.price}</option>)}
            </select>
            </Field>
          )
        )}

        <FieldGroup label="תמונת רקע" hint="אופציונלי">
        {form.image_url ? (
          <div style={{ position: 'relative' }}>
            <img src={form.image_url} alt="תצוגה מקדימה" style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 12, display: 'block' }} onError={e => { e.target.style.display = 'none' }} />
            <button type="button" aria-label="הסר תמונה" onClick={() => setForm(f => ({ ...f, image_url: '' }))} style={{
              position: 'absolute', top: 4, left: 4, background: 'rgba(0,0,0,0.6)', color: '#fff',
              border: 'none', borderRadius: '50%', width: 44, height: 44, fontSize: 16, cursor: 'pointer', lineHeight: 1,
            }}>✕</button>
          </div>
        ) : (
          <button type="button" className="btn btn-secondary" style={{ marginTop: 0 }} disabled={compressing} onClick={() => fileRef.current?.click()}>
            {compressing ? '...' : '🖼 העלה תמונת רקע'}
          </button>
        )}
        <input ref={fileRef} type="file" accept="image/*" hidden onChange={handleFile} aria-label="העלאת תמונת רקע" />
        </FieldGroup>
      </div>
    </Sheet>
  )
}

function ProductFeaturesEditor({ features, onChange }) {
  const [newFeature, setNewFeature] = useState('')

  function setFeatureState(text, state) {
    onChange(features.map(f => f.text === text ? { ...f, state } : f))
  }

  function moveFeature(idx, dir) {
    const arr = [...features]
    const to = idx + dir
    if (to < 0 || to >= arr.length) return
    ;[arr[idx], arr[to]] = [arr[to], arr[idx]]
    onChange(arr)
  }

  function addCustomFeature() {
    const text = newFeature.trim()
    if (!text || features.find(f => f.text === text)) return
    onChange([...features, { text, state: 'included' }])
    setNewFeature('')
  }

  function removeFeature(text) {
    onChange(features.filter(f => f.text !== text))
  }

  const STATES = [
    { state: 'included', icon: '✓', color: '#177a33', title: 'קיים' },
    { state: 'excluded', icon: '✗', color: '#c53030', title: 'לא קיים' },
    { state: 'plain', icon: '•', color: 'var(--hint)', title: 'טקסט בלבד (ללא אייקון)' },
  ]

  return (
    <FieldGroup label="תכונות המוצר" hint="✓ קיים · ✗ לא קיים · • טקסט בלבד">
      {features.map((item, idx) => (
        <div key={item.text} className="feat-row">
          <div className="feat-text">{item.text}</div>
          <div className="feat-ctrls">
            <div className="feat-grp">
              {STATES.map(s => (
                <button key={s.state} type="button" className="sheet-icon-btn" onClick={() => setFeatureState(item.text, s.state)}
                  aria-pressed={item.state === s.state} aria-label={`${s.title}: ${item.text}`} title={s.title}
                  style={item.state === s.state ? { borderColor: s.color, background: `${s.color}22`, color: s.color } : undefined}>{s.icon}</button>
              ))}
            </div>
            <div className="feat-grp">
              <button type="button" className="sheet-icon-btn" onClick={() => moveFeature(idx, -1)} disabled={idx === 0} aria-label={`הזז למעלה: ${item.text}`}>▲</button>
              <button type="button" className="sheet-icon-btn" onClick={() => moveFeature(idx, 1)} disabled={idx === features.length - 1} aria-label={`הזז למטה: ${item.text}`}>▼</button>
              <button type="button" className="sheet-icon-btn" onClick={() => removeFeature(item.text)} aria-label={`הסר: ${item.text}`} title="הסר">✕</button>
            </div>
          </div>
        </div>
      ))}

      <div className="feat-add">
        <input
          className="input"
          aria-label="תכונה חדשה"
          placeholder="הוסף תכונה חדשה..."
          value={newFeature}
          onChange={e => setNewFeature(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addCustomFeature()}
        />
        <button
          type="button"
          className="btn"
          aria-label="הוסף תכונה"
          disabled={!newFeature.trim()}
          onClick={addCustomFeature}
        >+</button>
      </div>
    </FieldGroup>
  )
}

function ProductModal({ title, form, setForm, saving, onSave, onClose, isNew }) {
  const fileRef = useRef(null)
  const [compressing, setCompressing] = useState(false)

  function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setCompressing(true)
    const reader = new FileReader()
    reader.onload = ev => {
      const img = new Image()
      img.onload = () => {
        const MAX = 800
        const ratio = Math.min(MAX / img.width, MAX / img.height, 1)
        const canvas = document.createElement('canvas')
        canvas.width  = Math.round(img.width  * ratio)
        canvas.height = Math.round(img.height * ratio)
        canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
        setForm(f => ({ ...f, image_url: canvas.toDataURL('image/jpeg', 0.82) }))
        setCompressing(false)
      }
      img.src = ev.target.result
    }
    reader.readAsDataURL(file)
  }

  const valid = form.name?.trim() && form.price !== '' && parseInt(form.price) >= 0

  return (
    <Sheet title={title} onClose={onClose} footer={<>
      <button className="btn" disabled={saving || !valid} onClick={onSave}>{saving ? '...' : 'שמור'}</button>
      <button className="btn btn-secondary" onClick={onClose}>ביטול</button>
    </>}>
      <div>
        <Field label="שם המוצר">
          <input className="input" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
        </Field>
        <Field label="תיאור המוצר">
          <textarea className="input" rows={3} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
        </Field>
        <Field label="מחיר (₪)">
          <input className="input" type="number" inputMode="numeric" min="0" dir="ltr" style={{ textAlign: 'start' }} value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} />
        </Field>

        <label style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14, fontSize: 14, minHeight: 44 }}>
          <input type="checkbox" style={{ width: 22, height: 22, flexShrink: 0 }} checked={form.is_active !== false} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
          מוצר פעיל
        </label>

        <Field label="סטטוס זמינות">
          <select className="input" value={form.availability_status || 'available'} onChange={e => setForm(f => ({ ...f, availability_status: e.target.value }))}>
            <option value="available">✅ זמין</option>
            <option value="coming_soon">🔜 בקרוב</option>
          </select>
        </Field>

        <Field label="אופן אספקה">
          <select className="input" value={form.delivery_type} onChange={e => setForm(f => ({ ...f, delivery_type: e.target.value }))}>
            <option value="auto">אוטומטי (ממאגר מלאי)</option>
            <option value="manual">ידני (אספקה על ידי מנהל)</option>
          </select>
        </Field>

        <Field label="הערת זמן משלוח" hint="לדוגמה: 14m3h">
          <input className="input" value={form.delivery_time_note} onChange={e => setForm(f => ({ ...f, delivery_time_note: e.target.value }))} />
        </Field>

        {form.delivery_type === 'manual' && (
          <Field label="כמות במלאי">
            <input className="input" type="number" inputMode="numeric" min="0" dir="ltr" style={{ textAlign: 'start' }} value={form.quantity_stock} onChange={e => setForm(f => ({ ...f, quantity_stock: e.target.value }))} />
          </Field>
        )}
        {form.delivery_type === 'auto' && (
          isNew ? (
            <Field label="מלאי התחלתי" hint='כל שורה = יחידת מלאי אחת (קוד/קישור). ניתן להוסיף עוד מלאי בהמשך דרך כפתור "📤 מלאי" בכרטיס המוצר.'>
              <textarea className="input" rows={4} dir="ltr" value={form.stock_text || ''} onChange={e => setForm(f => ({ ...f, stock_text: e.target.value }))} />
            </Field>
          ) : (
            <div className="field-hint" style={{ marginBottom: 14 }}>
              במצב אוטומטי המלאי מנוהל דרך כפתור "📤 מלאי" בכרטיס המוצר — כל שורה שתעלה שם היא יחידת מלאי אחת (קוד/קישור).
            </div>
          )
        )}

        <ProductFeaturesEditor
          features={form.features || []}
          onChange={features => setForm(f => ({ ...f, features }))}
        />

        <FieldGroup label="תמונה">
        {form.image_url ? (
          <div style={{ position: 'relative' }}>
            <img
              src={form.image_url}
              alt="תצוגה מקדימה"
              style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 12, display: 'block' }}
              onError={e => { e.target.style.display = 'none' }}
            />
            <button
              type="button"
              aria-label="הסר תמונה"
              onClick={() => setForm(f => ({ ...f, image_url: '' }))}
              style={{
                position: 'absolute', top: 4, left: 4,
                background: 'rgba(0,0,0,0.6)', color: '#fff',
                border: 'none', borderRadius: '50%', width: 44, height: 44,
                fontSize: 16, cursor: 'pointer', lineHeight: 1,
              }}
            >✕</button>
          </div>
        ) : (
          <button type="button" className="btn btn-secondary" style={{ marginTop: 0 }} disabled={compressing} onClick={() => fileRef.current?.click()}>
            {compressing ? '...' : '🖼 העלה תמונה'}
          </button>
        )}
        <input ref={fileRef} type="file" accept="image/*" hidden onChange={handleFile} aria-label="העלאת תמונה" />
        </FieldGroup>
      </div>
    </Sheet>
  )
}

function ProductStockModal({ product, onClose }) {
  const [text, setText] = useState('')
  const [units, setUnits] = useState(null)
  const [saving, setSaving] = useState(false)
  const [removingId, setRemovingId] = useState(null)

  function load() { adminFetchProductStock(product.id).then(setUnits).catch(() => setUnits([])) }
  useEffect(() => { load() }, [])

  const lines = text.split('\n').map(l => l.trim()).filter(Boolean)
  const unused = units?.filter(u => !u.is_used).length ?? 0
  const unusedUnits = units?.filter(u => !u.is_used) ?? []
  const usedUnits = units?.filter(u => u.is_used) ?? []

  async function upload() {
    if (!lines.length) return
    setSaving(true)
    try {
      await adminUploadProductStock(product.id, text)
      setText('')
      load()
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function removeUnit(unitId) {
    setRemovingId(unitId)
    try {
      await adminDeleteProductStockUnit(product.id, unitId)
      load()
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setRemovingId(null)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">📤 מלאי — {product.name}</div>
        <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 10 }}>
          {units === null ? 'טוען...' : `זמין: ${unused} / סה"כ: ${units.length}`}
        </div>

        {units !== null && units.length > 0 && (
          <div style={{ maxHeight: 220, overflowY: 'auto', marginBottom: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {unusedUnits.map(u => (
              <div key={u.id} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                background: 'var(--bg2)', borderRadius: 8, padding: '7px 10px',
              }}>
                <span style={{ flex: 1, minWidth: 0, fontSize: 12, fontFamily: 'monospace', wordBreak: 'break-all' }}>{u.content}</span>
                <button
                  type="button"
                  disabled={removingId === u.id}
                  onClick={() => removeUnit(u.id)}
                  style={{
                    flexShrink: 0, background: 'none', border: 'none', color: '#c53030',
                    cursor: removingId === u.id ? 'default' : 'pointer', fontSize: 15, padding: 4,
                    opacity: removingId === u.id ? 0.5 : 1,
                  }}
                  title="הסר יחידת מלאי"
                >🗑</button>
              </div>
            ))}
            {usedUnits.map(u => (
              <div key={u.id} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                background: 'var(--bg2)', borderRadius: 8, padding: '7px 10px', opacity: 0.5,
              }}>
                <span style={{ flex: 1, minWidth: 0, fontSize: 12, fontFamily: 'monospace', wordBreak: 'break-all', textDecoration: 'line-through' }}>{u.content}</span>
                <span style={{ flexShrink: 0, fontSize: 10, color: 'var(--hint)' }}>נמכר</span>
              </div>
            ))}
          </div>
        )}

        <textarea
          className="input"
          placeholder={'כל שורה = יחידת מלאי אחת (קוד / קישור)'}
          rows={6}
          value={text}
          onChange={e => setText(e.target.value)}
        />
        <div style={{ fontSize: 11, color: 'var(--hint)', marginBottom: 10 }}>{lines.length} שורות</div>
        <button className="btn" disabled={saving || !lines.length} onClick={upload}>{saving ? '...' : `➕ הוסף ${lines.length || ''} יחידות`}</button>
        <button className="btn btn-secondary" style={{ marginTop: 8 }} onClick={onClose}>סגור</button>
      </div>
    </div>
  )
}

function ChipsEditor({ chips, onChange, isFree, suggestions = [] }) {
  const [newChip, setNewChip] = useState('')

  function addChip() {
    const text = newChip.trim()
    if (!text || chips.includes(text)) return
    onChange([...chips, text])
    setNewChip('')
  }

  function removeChip(text) {
    onChange(chips.filter(c => c !== text))
  }

  const availableSuggestions = suggestions.filter(s => !chips.includes(s))

  return (
    <FieldGroup label="ציפים" hint={isFree ? 'הציפ "X חיפושים נותרו" מוצג אוטומטית' : undefined}>
      {/* Current chips */}
      {chips.length > 0 && (
        <div className="sheet-chips" style={{ marginBottom: 10 }}>
          {chips.map(chip => (
            <span key={chip} className="sheet-chip">
              {chip}
              <button type="button" aria-label={`הסר ציפ: ${chip}`} onClick={() => removeChip(chip)}>✕</button>
            </span>
          ))}
        </div>
      )}

      {/* Suggestions from other packages */}
      {availableSuggestions.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <div className="field-hint" style={{ marginTop: 0, marginBottom: 6 }}>בחר מהרשימה:</div>
          <div className="sheet-chips">
            {availableSuggestions.map(s => (
              <button key={s} type="button" className="sheet-chip-add" onClick={() => onChange([...chips, s])}>+ {s}</button>
            ))}
          </div>
        </div>
      )}

      {/* Add new */}
      <div className="feat-add">
        <input
          className="input"
          aria-label="ציפ חדש"
          placeholder='לדוגמה: 💳 חד-פעמי'
          value={newChip}
          onChange={e => setNewChip(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addChip()}
        />
        <button type="button" className="btn" aria-label="הוסף ציפ" disabled={!newChip.trim()} onClick={addChip}>+</button>
      </div>
    </FieldGroup>
  )
}

function PackageModal({ title, form, setForm, saving, onSave, onClose, suggestions = [] }) {
  const fileRef = useRef(null)
  const [compressing, setCompressing] = useState(false)
  const [newFeature, setNewFeature] = useState('')

  const features = form.features || []

  // 'included' | 'excluded' | 'off'
  // Active = in features array (included or excluded), in stored order
  // Inactive = DEFAULT_PKG_FEATURES not yet in features array
  const activeFeatures   = features  // already ordered
  const inactiveDefaults = DEFAULT_PKG_FEATURES.filter(t => !features.find(f => f.text === t))

  function setFeatureState(text, state) {
    setForm(f => {
      const cur = (f.features || []).filter(x => x.text !== text)
      if (state === 'off') return { ...f, features: cur }
      // if activating, keep existing position or append
      const existing = (f.features || []).find(x => x.text === text)
      if (existing) return { ...f, features: (f.features || []).map(x => x.text === text ? { ...x, included: state === 'included' } : x) }
      return { ...f, features: [...cur, { text, included: state === 'included' }] }
    })
  }

  function moveFeature(idx, dir) {
    setForm(f => {
      const arr = [...(f.features || [])]
      const to = idx + dir
      if (to < 0 || to >= arr.length) return f
      ;[arr[idx], arr[to]] = [arr[to], arr[idx]]
      return { ...f, features: arr }
    })
  }

  function addCustomFeature() {
    const text = newFeature.trim()
    if (!text || features.find(f => f.text === text)) return
    setForm(f => ({ ...f, features: [...(f.features || []), { text, included: true }] }))
    setNewFeature('')
  }

  function removeFeature(text) {
    setForm(f => ({ ...f, features: (f.features || []).filter(x => x.text !== text) }))
  }

  function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setCompressing(true)
    const reader = new FileReader()
    reader.onload = ev => {
      const img = new Image()
      img.onload = () => {
        const MAX = 800
        const ratio = Math.min(MAX / img.width, MAX / img.height, 1)
        const canvas = document.createElement('canvas')
        canvas.width  = Math.round(img.width  * ratio)
        canvas.height = Math.round(img.height * ratio)
        canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
        setForm(f => ({ ...f, image_url: canvas.toDataURL('image/jpeg', 0.82) }))
        setCompressing(false)
      }
      img.src = ev.target.result
    }
    reader.readAsDataURL(file)
  }

  const isFreePkg = form.searches === '0'
  const isUnlimited = parseInt(form.searches) === -1

  return (
    <Sheet title={title} onClose={onClose} footer={<>
      <button className="btn" disabled={saving} onClick={onSave}>{saving ? '...' : 'שמור'}</button>
      <button className="btn btn-secondary" onClick={onClose}>ביטול</button>
    </>}>
      <div>
        <Field label="שם המוצר">
          <input className="input" value={form.label} onChange={e => setForm(f => ({ ...f, label: e.target.value }))} />
        </Field>
        {!isFreePkg && (
          <>
            <div className="field-row">
              <Field label="חיפושים" hint="-1 = בלתי מוגבל">
                <input className="input" type="number" inputMode="numeric" dir="ltr" style={{ textAlign: 'start' }} value={form.searches} onChange={e => setForm(f => ({ ...f, searches: e.target.value }))} />
              </Field>
              <Field label="מחיר (₪)">
                <input className="input" type="number" inputMode="numeric" min="0" dir="ltr" style={{ textAlign: 'start' }} value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} />
              </Field>
            </div>
            {isUnlimited && (
              <Field label="משך בחודשים" hint="ברירת מחדל: 1">
                <input className="input" type="number" inputMode="numeric" min="1" dir="ltr" style={{ textAlign: 'start' }} value={form.duration_months ?? '1'} onChange={e => setForm(f => ({ ...f, duration_months: e.target.value }))} />
              </Field>
            )}
          </>
        )}

        <FieldGroup label="תמונה">
        {form.image_url ? (
          <div style={{ position: 'relative' }}>
            <img
              src={form.image_url}
              alt="תצוגה מקדימה"
              style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 12, display: 'block' }}
              onError={e => { e.target.style.display = 'none' }}
            />
            <button
              type="button"
              aria-label="הסר תמונה"
              onClick={() => setForm(f => ({ ...f, image_url: '' }))}
              style={{
                position: 'absolute', top: 4, left: 4,
                background: 'rgba(0,0,0,0.6)', color: '#fff',
                border: 'none', borderRadius: '50%', width: 44, height: 44,
                fontSize: 16, cursor: 'pointer', lineHeight: 1,
              }}
            >✕</button>
          </div>
        ) : (
          <>
            <button type="button" className="btn btn-secondary" style={{ marginTop: 0 }} disabled={compressing} onClick={() => fileRef.current?.click()}>
              {compressing ? '⏳ מכווץ...' : '📷 העלאה מהמכשיר'}
            </button>
            <input
              className="input"
              style={{ marginTop: 8 }}
              aria-label="או הדבק כתובת URL של תמונה"
              dir="ltr"
              placeholder="או הדבק כתובת URL"
              value={form.image_url}
              onChange={e => setForm(f => ({ ...f, image_url: e.target.value }))}
            />
          </>
        )}
        <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFile} aria-label="העלאת תמונה" />
        </FieldGroup>

        {/* Chips */}
        <ChipsEditor chips={form.chips || []} onChange={chips => setForm(f => ({ ...f, chips }))} isFree={isFreePkg} suggestions={suggestions} />

        {/* Features */}
        <FieldGroup label="תכונות המוצר" hint="✓ קיים · ✗ לא קיים · ריק = מוסתר">
          {/* Active features — ordered list with ↑↓ */}
          {activeFeatures.map((item, idx) => {
            const state = item.included ? 'included' : 'excluded'
            return (
              <div key={item.text} className="feat-row">
                <div className="feat-text">{item.text}</div>
                <div className="feat-ctrls">
                  <div className="feat-grp">
                    <button type="button" className="sheet-icon-btn" onClick={() => setFeatureState(item.text, 'included')} aria-pressed={state === 'included'} aria-label={`קיים: ${item.text}`} title="קיים"
                      style={state === 'included' ? { borderColor: '#177a33', background: '#177a3322', color: '#177a33' } : undefined}>✓</button>
                    <button type="button" className="sheet-icon-btn" onClick={() => setFeatureState(item.text, 'excluded')} aria-pressed={state === 'excluded'} aria-label={`לא קיים: ${item.text}`} title="לא קיים"
                      style={state === 'excluded' ? { borderColor: '#c53030', background: '#c5303022', color: '#c53030' } : undefined}>✗</button>
                  </div>
                  <div className="feat-grp">
                    <button type="button" className="sheet-icon-btn" onClick={() => moveFeature(idx, -1)} disabled={idx === 0} aria-label={`הזז למעלה: ${item.text}`}>▲</button>
                    <button type="button" className="sheet-icon-btn" onClick={() => moveFeature(idx, 1)} disabled={idx === activeFeatures.length - 1} aria-label={`הזז למטה: ${item.text}`}>▼</button>
                    <button type="button" className="sheet-icon-btn" onClick={() => removeFeature(item.text)} aria-label={`הסר מהרשימה: ${item.text}`} title="הסר מהרשימה">✕</button>
                  </div>
                </div>
              </div>
            )
          })}

          {/* Inactive defaults — click to add */}
          {inactiveDefaults.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <div className="field-hint" style={{ marginTop: 0, marginBottom: 6 }}>לחץ להוספה לרשימה:</div>
              {inactiveDefaults.map(feat => (
                <div key={feat} className="feat-row" style={{ borderStyle: 'dashed' }}>
                  <div className="feat-text is-off">{feat}</div>
                  <div className="feat-grp">
                    <button type="button" className="sheet-icon-btn" onClick={() => setFeatureState(feat, 'included')} aria-label={`הוסף כקיים: ${feat}`} title="הוסף כקיים">✓</button>
                    <button type="button" className="sheet-icon-btn" onClick={() => setFeatureState(feat, 'excluded')} aria-label={`הוסף כלא קיים: ${feat}`} title="הוסף כלא קיים">✗</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Add new custom feature */}
          <div className="feat-add">
            <input
              className="input"
              aria-label="תכונה חדשה"
              placeholder="הוסף תכונה חדשה..."
              value={newFeature}
              onChange={e => setNewFeature(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addCustomFeature()}
            />
            <button type="button" className="btn" aria-label="הוסף תכונה" disabled={!newFeature.trim()} onClick={addCustomFeature}>+</button>
          </div>
        </FieldGroup>

        {/* Active toggle */}
        {!isFreePkg && (
          <button
            type="button" role="switch" aria-checked={form.is_active !== false}
            onClick={() => setForm(f => ({ ...f, is_active: f.is_active === false }))}
            style={{
              display: 'flex', alignItems: 'center', gap: 10, width: '100%', textAlign: 'start', fontFamily: 'inherit',
              background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 12, padding: '10px 14px',
              minHeight: 56, cursor: 'pointer', userSelect: 'none', color: 'var(--text-main)',
            }}
          >
            <span style={{ flex: 1, minWidth: 0 }}>
              <span style={{ display: 'block', fontSize: 14, fontWeight: 700 }}>מוצר פעיל</span>
              <span style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                {form.is_active !== false ? 'מוצג לכל המשתמשים' : 'מוסתר — לא מוצג בדף המוצרים'}
              </span>
            </span>
            <span aria-hidden="true" style={{
              width: 44, height: 24, borderRadius: 12, flexShrink: 0,
              background: form.is_active !== false ? '#177a33' : 'rgba(0,100,200,0.18)',
              position: 'relative', transition: 'background 0.2s',
            }}>
              <span style={{
                position: 'absolute', top: 3, width: 18, height: 18, borderRadius: '50%',
                background: '#fff', transition: 'left 0.2s',
                left: form.is_active !== false ? 23 : 3,
              }} />
            </span>
          </button>
        )}
      </div>
    </Sheet>
  )
}

function grantTypeLabel(searches) {
  if (searches === 0) return 'איפוס למסלול החינמי'
  if (searches === -1) return 'מסלול Premium לתקופה (חודש כברירת מחדל)'
  if (searches === -2) return 'Premium קבוע ללא תפוגה'
  return `הוספת ${searches} חיפושים`
}

function grantBadge(searches) {
  if (searches === 0) return { text: 'איפוס', tone: 'mute' }
  if (searches === -1) return { text: 'Premium לחודש', tone: 'good' }
  if (searches === -2) return { text: 'Premium קבוע', tone: 'warn' }
  return { text: `+${searches} חיפושים`, tone: '' }
}

function AdminGrantsTab() {
  const [grants, setGrants] = useState(null)
  const [editing, setEditing] = useState(null)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ label: '', searches: '' })
  const [saving, setSaving] = useState(false)
  const [dragIdx, setDragIdx] = useState(null)
  const [reordering, setReordering] = useState(false)
  const [confirmId, setConfirmId] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [codesOpen, setCodesOpen] = useState(false)
  const [giftOpen, setGiftOpen]   = useState(false)
  const [unlimitedOpen, setUnlimitedOpen] = useState(false)

  useEffect(() => { adminFetchGrants().then(setGrants).catch(() => {}) }, [])

  async function applyReorder(next) {
    setGrants(next)
    setReordering(true)
    try {
      setGrants(await adminReorderGrants(next.map(g => g.id)))
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה בעדכון הסדר')
      setGrants(await adminFetchGrants())
    }
    setReordering(false)
  }

  function moveGrant(fromIdx, toIdx) {
    if (fromIdx === toIdx || fromIdx < 0 || toIdx < 0 || !grants) return
    const next = [...grants]
    const [moved] = next.splice(fromIdx, 1)
    next.splice(toIdx, 0, moved)
    applyReorder(next)
  }

  async function saveEdit() {
    setSaving(true)
    try {
      await adminUpdateGrant(editing.id, { label: form.label, searches: parseInt(form.searches) })
      setGrants(await adminFetchGrants())
      setEditing(null)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function saveAdd() {
    setSaving(true)
    try {
      setGrants(await adminAddGrant({ label: form.label, searches: parseInt(form.searches) }))
      setAdding(false)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function deleteGrant(id) {
    // confirmation is the inline step on the card (confirmId)
    setDeleting(true)
    try {
      await adminDeleteGrant(id)
      setGrants(await adminFetchGrants())
      setConfirmId(null)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה במחיקת ההטבה') }
    setDeleting(false)
  }

  if (!grants) return <div className="loading"></div>

  return (
    <div className="tab-fade-in">
      <div className="card" style={{ padding: '20px', marginBottom: 24, background: 'linear-gradient(to right, rgba(99, 102, 241, 0.05), transparent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <span style={{ fontSize: 24 }}>🎁</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>הטבות מנהל</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>הטבות מוכנות שמעניקים ידנית למשתמשים</div>
          </div>
        </div>
        <details className="admin-help">
          <summary>מה המשמעות של הערכים?</summary>
          <ul>
            <li><span className="val">0</span><span>איפוס למסלול החינמי</span></li>
            <li><span className="val">-1</span><span>מסלול Premium לתקופה (חודש כברירת מחדל)</span></li>
            <li><span className="val">-2</span><span>Premium קבוע, ללא תפוגה</span></li>
            <li><span className="val">1+</span><span>הוספת חיפושים (מספר חיובי)</span></li>
          </ul>
          <p className="note">מסלול Premium = חיפושים ללא הגבלה וכל יכולות הפרימיום לתקופה.</p>
        </details>
      </div>
      
      <div className="admin-item-list">
        {grants.map((g, idx) => {
          const isDragging = dragIdx === idx
          const badge = grantBadge(g.searches)
          return (
            <AdminItemCard
              key={g.id}
              draggable={!reordering}
              onDragStart={() => setDragIdx(idx)}
              onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move' }}
              onDrop={() => { if (dragIdx !== null) moveGrant(dragIdx, idx); setDragIdx(null) }}
              onDragEnd={() => setDragIdx(null)}
              className={isDragging ? 'dragging' : ''}
              style={{ cursor: reordering ? 'wait' : 'grab' }}
              leading={<span aria-label={`מספר ${idx + 1}`}>{idx + 1}</span>}
              title={g.label}
              badge={<bdi>{badge.text}</bdi>}
              badgeTone={badge.tone}
              subtitle={grantTypeLabel(g.searches)}
              actions={<>
                <AdminItemBtn icon="▲" label="למעלה" ariaLabel={`הזז למעלה: ${g.label}`} disabled={idx === 0 || reordering} onClick={() => moveGrant(idx, idx - 1)} />
                <AdminItemBtn icon="▼" label="למטה" ariaLabel={`הזז למטה: ${g.label}`} disabled={idx === grants.length - 1 || reordering} onClick={() => moveGrant(idx, idx + 1)} />
                <AdminItemBtn icon="✏️" label="ערוך" ariaLabel={`ערוך הטבה: ${g.label}`} onClick={() => { setEditing(g); setForm({ label: g.label, searches: String(g.searches) }) }} />
                <AdminItemBtn icon="🗑️" label="מחק" ariaLabel={`מחק הטבה: ${g.label}`} danger onClick={() => setConfirmId(g.id)} />
              </>}
              footer={confirmId === g.id && (
                <AdminItemConfirm text="למחוק את ההטבה? אי אפשר לבטל." busy={deleting}
                  onYes={() => deleteGrant(g.id)} onNo={() => setConfirmId(null)} />
              )}
            />
          )
        })}
      </div>
      
      <button className="btn btn-success" onClick={() => { setAdding(true); setForm({ label: '', searches: '' }) }} style={{ padding: '16px', fontSize: 15, fontWeight: 800, borderRadius: 16, width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
        <span style={{ fontSize: 20 }}>➕</span> הוסף תוכנית הטבה חדשה
      </button>

      {/* Gift all section */}
      <div style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
        <button
          onClick={() => setGiftOpen(o => !o)}
          style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 0, color: 'var(--text)' }}
        >
          <span style={{ fontSize: 15, fontWeight: 700 }}>🎁 הענק מתנה לכל המשתמשים</span>
          <span style={{ fontSize: 12, color: 'var(--hint)' }}>{giftOpen ? '▲' : '▼'}</span>
        </button>
        {giftOpen && <GiftAllSection onDone={() => setGiftOpen(false)} />}
      </div>

      {/* Global unlimited-for-everyone section */}
      <div style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
        <button
          onClick={() => setUnlimitedOpen(o => !o)}
          style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 0, color: 'var(--text)' }}
        >
          <span style={{ fontSize: 15, fontWeight: 700 }}>♾️ ללא הגבלת חיפושים לכולם</span>
          <span style={{ fontSize: 12, color: 'var(--hint)' }}>{unlimitedOpen ? '▲' : '▼'}</span>
        </button>
        {unlimitedOpen && <GlobalUnlimitedSection />}
      </div>

      {/* Codes section */}
      <div style={{ marginTop: 16, borderTop: '1px solid var(--border)', paddingTop: 16 }}>
        <button
          onClick={() => setCodesOpen(o => !o)}
          style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 0, color: 'var(--text)' }}
        >
          <span style={{ fontSize: 15, fontWeight: 700 }}>🔑 קודי הפעלה</span>
          <span style={{ fontSize: 12, color: 'var(--hint)' }}>{codesOpen ? '▲' : '▼'}</span>
        </button>
        {codesOpen && <CodesSection />}
      </div>

      {editing && (
        <AdminGrantModal title="✏️ עריכת הטבה" form={form} setForm={setForm} saving={saving} onSave={saveEdit} onClose={() => setEditing(null)} />
      )}
      {adding && (
        <AdminGrantModal title="➕ הטבה חדשה" form={form} setForm={setForm} saving={saving} onSave={saveAdd} onClose={() => setAdding(false)} />
      )}
    </div>
  )
}

function AdminGrantModal({ title, form, setForm, saving, onSave, onClose }) {
  return (
    <Sheet title={title} onClose={onClose} footer={<>
      <button className="btn" disabled={saving || !form.label.trim()} onClick={onSave}>{saving ? '...' : 'שמור'}</button>
      <button className="btn btn-secondary" onClick={onClose}>ביטול</button>
    </>}>
      <Field label="שם ההטבה">
        <input className="input" value={form.label} onChange={e => setForm(f => ({ ...f, label: e.target.value }))} />
      </Field>
      <Field label="חיפושים" hint="0 = איפוס לחינמי · -1 = Premium לתקופה (חודש) · -2 = Premium קבוע · מספר חיובי = הוספת חיפושים">
        <input className="input" type="number" inputMode="numeric" dir="ltr" style={{ textAlign: 'start' }} value={form.searches} onChange={e => setForm(f => ({ ...f, searches: e.target.value }))} />
      </Field>
    </Sheet>
  )
}

const STATUS_META = {
  intent:    { label: 'ממתין לתשלום', color: '#636366' },
  created:   { label: 'ממתין לתשלום', color: '#636366' },
  approved:  { label: 'אושר',    color: '#2196F3' },
  captured:  { label: 'נגבה',    color: '#00bcd4' },
  completed: { label: 'הושלם',   color: '#27692b' },
  failed:    { label: 'נכשל',    color: '#f44336' },
  expired:   { label: 'פג תוקף', color: '#9a4a07' },
  declined:  { label: 'נדחה',    color: '#f44336' },
  cancelled:        { label: 'בוטל',               color: '#9a4a07' },
  user_cancelled:   { label: 'בוטל ע״י משתמש',    color: '#9a4a07' },
  admin_approved:   { label: 'אושר ע״י מנהל',  color: '#27692b' },
  admin_cancelled:  { label: 'בוטל ע״י מנהל',  color: '#9a4a07' },
  pending_delivery: { label: 'ממתין למשלוח',   color: '#9a4a07' },
}

function PaypalTransactionRow({ tx, onRefresh }) {
  const [open, setOpen] = useState(false)
  const [working, setWorking] = useState(false)
  const [deliverText, setDeliverText] = useState('')
  const [delivering, setDelivering] = useState(false)
  const meta = STATUS_META[tx.status] || { label: tx.status, color: '#636366' }
  const canAct = ['intent', 'created', 'cancelled'].includes(tx.status)
  const needsDelivery = tx.package_type === 'product' && tx.status === 'pending_delivery'

  async function approve(e) {
    e.stopPropagation()
    if (working) return
    setWorking(true)
    try { await adminOrderApprove(tx.ref); onRefresh?.() } catch { alert('שגיאה') }
    setWorking(false)
  }

  async function cancel(e) {
    e.stopPropagation()
    if (working) return
    setWorking(true)
    try { await adminOrderCancel(tx.ref); onRefresh?.() } catch { alert('שגיאה') }
    setWorking(false)
  }

  async function sendDelivery(e) {
    e.stopPropagation()
    if (delivering || !deliverText.trim()) return
    setDelivering(true)
    try { await adminDeliverOrder(tx.ref, deliverText.trim()); setDeliverText(''); onRefresh?.() } catch { alert('שגיאה') }
    setDelivering(false)
  }

  return (
    <div
      className="card"
      style={{ padding: 0, marginBottom: 12, overflow: 'hidden', cursor: 'pointer', transition: 'all 0.2s', borderLeft: `4px solid ${meta.color}` }}
      onClick={() => setOpen(o => !o)}
    >
      <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontFamily: 'monospace', fontSize: 14, fontWeight: 800, color: 'var(--text-main)', background: 'var(--bg)', padding: '4px 8px', borderRadius: 8, letterSpacing: '0.5px' }}>#{tx.ref}</span>
            <span style={{ background: `${meta.color}20`, color: meta.color, border: `1px solid ${meta.color}40`, borderRadius: 12, padding: '4px 10px', fontSize: 12, fontWeight: 800 }}>{meta.label}</span>
          </div>
          <span style={{ color: '#047857', fontWeight: 800, fontSize: 18 }}>₪{tx.amount}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-main)' }}>{tx.label}</span>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{fmtDateTime(tx.created_at)}</span>
        </div>
        <div style={{ fontSize: 13, color: 'var(--hint)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <span>👤</span>
          <span>{tx.username ? `@${tx.username}` : tx.full_name || `משתמש ${tx.user_id}`}</span>
        </div>
      </div>
      
      {open && (
        <div style={{ borderTop: '1px solid var(--border)', padding: '20px', background: 'rgba(0,0,0,0.02)' }} onClick={e => e.stopPropagation()}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, background: 'var(--bg-card)', padding: '16px', borderRadius: 16, border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 600 }}>PayPal Order ID:</span>
              <span style={{ fontFamily: 'monospace', fontSize: 13, color: 'var(--text-main)', fontWeight: 700 }}>{tx.paypal_order_id || '—'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 600 }}>חיפושים/מוצר:</span>
              <span style={{ color: 'var(--text-main)', fontSize: 13, fontWeight: 700 }}>{tx.searches === -1 ? '♾️ ללא הגבלה' : tx.searches}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 600 }}>עדכון אחרון:</span>
              <span style={{ color: 'var(--text-main)', fontSize: 13, fontWeight: 700 }}>{fmtDateTime(tx.updated_at)}</span>
            </div>
          </div>
          
          {tx.error && (
            <div style={{ marginTop: 12, padding: '12px', background: 'rgba(239, 68, 68, 0.1)', color: '#c53030', borderRadius: 12, border: '1px dashed rgba(239, 68, 68, 0.3)', fontSize: 13, fontWeight: 600 }}>
              ⚠️ {tx.error}
            </div>
          )}
          
          {needsDelivery && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-main)', marginBottom: 8 }}>📦 מסירת מוצר דיגיטלי ללקוח:</div>
              <textarea
                className="input"
                style={{ marginBottom: 12, fontSize: 14, borderRadius: 12, minHeight: 80 }}
                placeholder="הכנס את תוכן המשלוח (קוד, קישור, או כל פרט אחר) שיישלח ישירות ללקוח בהודעה..."
                value={deliverText}
                onChange={e => setDeliverText(e.target.value)}
              />
              <button
                onClick={sendDelivery}
                disabled={delivering || !deliverText.trim()}
                style={{ width: '100%', padding: '12px 0', background: '#047857', color: '#fff', border: 'none', borderRadius: 12, fontSize: 14, fontWeight: 800, cursor: delivering ? 'default' : 'pointer', opacity: delivering || !deliverText.trim() ? 0.5 : 1, transition: 'all 0.2s', boxShadow: '0 4px 12px rgba(16, 185, 129, 0.2)' }}
              >
                {delivering ? '⏳ שולח...' : '✨ אשרו ושלחו ללקוח'}
              </button>
            </div>
          )}
          
          {canAct && (
            <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
              <button
                onClick={approve}
                disabled={working}
                style={{ flex: 1, padding: '12px 0', background: 'rgba(16, 185, 129, 0.1)', color: '#047857', border: 'none', borderRadius: 12, fontSize: 14, fontWeight: 800, cursor: working ? 'default' : 'pointer', opacity: working ? 0.5 : 1 }}
              >✅ אישור מנהל ידני</button>
              <button
                onClick={cancel}
                disabled={working}
                style={{ flex: 1, padding: '12px 0', background: 'rgba(239, 68, 68, 0.1)', color: '#c53030', border: 'none', borderRadius: 12, fontSize: 14, fontWeight: 800, cursor: working ? 'default' : 'pointer', opacity: working ? 0.5 : 1 }}
              >🚫 ביטול מנהל</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function PaymentsTab() {
  const [txs, setTxs] = useState(null)

  function load() { adminFetchPaypalTransactions().then(setTxs).catch(() => setTxs([])) }
  useEffect(() => { load() }, [])

  return (
    <div className="tab-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>היסטוריית רכישות</div>
          <div style={{ fontSize: 13, color: 'var(--hint)', marginTop: 4 }}>{txs ? `${txs.length} עסקאות פעילות וישנות` : 'טוען נתונים...'}</div>
        </div>
        <button className="btn" style={{ width: 44, height: 44, padding: 0, margin: 0, borderRadius: 14, fontSize: 18, background: 'var(--bg-card)', border: '1px solid var(--border)' }} onClick={load} title="רענן נתונים">🔄</button>
      </div>
      {!txs && <div className="loading"></div>}
      {txs?.length === 0 && <div style={{ color: 'var(--hint)', textAlign: 'center', padding: 40, background: 'var(--bg-card)', borderRadius: 16, border: '1px dashed var(--border)', fontSize: 14 }}>אין עסקאות במערכת עדיין.</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {txs?.map(tx => <PaypalTransactionRow key={tx.id} tx={tx} onRefresh={load} />)}
      </div>
    </div>
  )
}

function CodesSection({ standalone }) {
  const [codes, setCodes] = useState(null)
  const [form, setForm] = useState({ searches: 50, unlimited: false, single_use: true, monthly: false })
  const [creating, setCreating] = useState(false)
  const [confirmCode, setConfirmCode] = useState(null)
  const [deletingCode, setDeletingCode] = useState(false)

  function load() { adminFetchCodes().then(setCodes).catch(() => {}) }
  useEffect(() => { load() }, [])

  async function createCode() {
    setCreating(true)
    try {
      const res = await adminCreateCode(form)
      window.Telegram?.WebApp?.showAlert(`✅ קוד נוצר:\n${res.code}`)
      load()
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setCreating(false)
  }

  async function deleteCode(code) {
    // confirmation is the inline step on the card (confirmCode)
    setDeletingCode(true)
    try { await adminDeleteCode(code); load(); setConfirmCode(null) }
    catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setDeletingCode(false)
  }

  function copyCode(code) {
    navigator.clipboard?.writeText(code).catch(() => {})
    window.Telegram?.WebApp?.showAlert(`✅ הועתק:\n${code}`)
  }

  if (!codes) return <div className="loading"></div>

  return (
    <div className="tab-fade-in" style={{ marginTop: 24 }}>
      {/* Create code */}
      <div className="card" style={{ padding: '20px', marginBottom: 24, background: 'linear-gradient(to right, rgba(99, 102, 241, 0.05), transparent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <span style={{ fontSize: 24 }}>🎟️</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>קופונים וקודים</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>יצירת קודי הטבה ללקוחות</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 700, marginBottom: 6 }}>כמות חיפושים</div>
            <input
              className="input"
              type="number"
              min="1"
              placeholder="לדוגמה: 50"
              value={form.searches}
              onChange={e => setForm(f => ({ ...f, searches: parseInt(e.target.value) || 50 }))}
              style={{ margin: 0, height: 44, borderRadius: 12 }}
              disabled={form.unlimited}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button
              className="btn"
              disabled={creating}
              onClick={createCode}
              style={{ margin: 0, height: 44, padding: '0 24px', borderRadius: 12, background: 'var(--primary)', fontWeight: 700, fontSize: 14 }}
            >
              {creating ? '⏳ מייצר...' : '➕ צור קוד'}
            </button>
          </div>
        </div>
        
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, background: 'var(--bg)', padding: '12px', borderRadius: 12, border: '1px solid var(--border)' }}>
          {[['unlimited', '♾️ Premium קבוע'], ['monthly', '📅 Premium לחודש'], ['single_use', '1️⃣ קוד חד-פעמי']].map(([key, label]) => (
            <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, cursor: 'pointer', fontWeight: form[key] ? 700 : 500, color: form[key] ? 'var(--text-main)' : 'var(--text-muted)' }}>
              <div style={{ width: 18, height: 18, borderRadius: 4, border: `2px solid ${form[key] ? 'var(--primary)' : 'var(--border)'}`, background: form[key] ? 'var(--primary)' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s' }}>
                {form[key] && <span style={{ color: '#fff', fontSize: 12 }}>✓</span>}
              </div>
              <input
                type="checkbox"
                checked={form[key]}
                onChange={e => setForm(f => ({ ...f, [key]: e.target.checked, ...(key === 'unlimited' ? { monthly: false } : {}) }))}
                style={{ display: 'none' }}
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      {/* Code list */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)' }}>רשימת קודים</div>
        <div style={{ fontSize: 13, color: 'var(--hint)', background: 'var(--bg-card)', padding: '4px 12px', borderRadius: 20, border: '1px solid var(--border)' }}>{codes.length} קודים במערכת</div>
      </div>
      
      {codes.length === 0 && (
        <div style={{ color: 'var(--hint)', textAlign: 'center', padding: 40, background: 'var(--bg-card)', borderRadius: 16, border: '1px dashed var(--border)' }}>
          אין קודים פעילים או שהיו בשימוש
        </div>
      )}

      <div className="admin-item-list">
        {codes.map(c => {
          const used = c.used_by != null
          const expired = c.expires && new Date(c.expires) < new Date()
          const status = used ? 'נוצל' : expired ? 'פג תוקף' : 'פעיל'
          const tone = used ? '' : expired ? 'mute' : 'good'
          const desc = c.unlimited ? (c.monthly ? 'מסלול Premium לחודש' : 'Premium קבוע ללא תפוגה') : `${c.searches} חיפושים`

          return (
            <AdminItemCard
              key={c.code}
              style={{ opacity: (used || expired) ? 0.75 : 1 }}
              title={<span dir="ltr" style={{ fontFamily: 'monospace', letterSpacing: 1, unicodeBidi: 'isolate' }}>{c.code}</span>}
              badge={status}
              badgeTone={tone}
              subtitle={`${desc}${c.single_use ? ' · לשימוש חד-פעמי' : ''}`}
              cols={2}
              actions={<>
                <AdminItemBtn icon="📋" label="העתק" ariaLabel={`העתק קוד ${c.code}`} onClick={() => copyCode(c.code)} />
                <AdminItemBtn icon="🗑️" label="מחק" ariaLabel={`מחק קוד ${c.code}`} danger onClick={() => setConfirmCode(c.code)} />
              </>}
              footer={confirmCode === c.code && (
                <AdminItemConfirm text="למחוק את הקוד? אי אפשר לבטל." busy={deletingCode}
                  onYes={() => deleteCode(c.code)} onNo={() => setConfirmCode(null)} />
              )}
            />
          )
        })}
      </div>
    </div>
  )
}

function GlobalUnlimitedSection() {
  const [settings, setSettings] = useState(null)
  const [enabled, setEnabled]   = useState(false)
  const [noEnd, setNoEnd]       = useState(false)
  const [start, setStart]       = useState('')
  const [end, setEnd]           = useState('')
  const [label, setLabel]       = useState('')
  const [saving, setSaving]     = useState(false)

  useEffect(() => {
    adminFetchSettings().then(s => {
      setSettings(s)
      setEnabled(!!s.global_unlimited_enabled)
      setStart(s.global_unlimited_start || '')
      setEnd(s.global_unlimited_end || '')
      setNoEnd(!s.global_unlimited_end)
      setLabel(s.global_unlimited_label || '')
    }).catch(() => {})
  }, [])

  function status() {
    if (!settings || !enabled) return null
    const today = new Date().toISOString().slice(0, 10)
    const e = noEnd ? '' : end
    const startOk = !start || today >= start
    const endOk   = !e || today <= e
    if (startOk && endOk) return 'active'
    if (start && today < start) return 'upcoming'
    return 'expired'
  }

  async function save(nextEnabled) {
    setSaving(true)
    try {
      const payload = {
        global_unlimited_enabled: nextEnabled,
        global_unlimited_start:   start,
        global_unlimited_end:     noEnd ? '' : end,
        global_unlimited_label:   label,
      }
      await adminUpdateSettings(payload)
      setEnabled(nextEnabled)
      setSettings(s => ({ ...s, ...payload }))
      window.Telegram?.WebApp?.showAlert(nextEnabled ? '✅ ההטבה הופעלה לכל המשתמשים' : '✅ ההטבה בוטלה לכל המשתמשים')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  function cancelNow() {
    window.Telegram?.WebApp?.showConfirm('לבטל את ההטבה לכולם באופן מיידי?', ok => {
      if (ok) save(false)
    })
  }

  if (!settings) return <div className="loading"></div>

  const STATUS_COLORS = { active: '#177a33', upcoming: '#975a16', expired: '#c53030' }
  const STATUS_LABELS = { active: '🟢 פעיל כעת לכל המשתמשים', upcoming: '🟡 טרם התחיל', expired: '🔴 הסתיים (התאריך חלף)' }
  const st = status()

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 12, lineHeight: 1.5 }}>
        מעניק לכל המשתמשים — קיימים וחדשים — גישה ללא הגבלת חיפושים וגם לתכונות המיועדות למנויים (מחיר שוק, דוח PDF, התראות),
        מבלי לגעת ביתרה האישית שלהם או במנויים האמיתיים ששילמו. ברגע שמבטלים (בכל שלב), כל משתמש חוזר בדיוק למצב שהיה לו לפני ההטבה.
      </div>

      {st && (
        <div style={{ marginBottom: 12, fontSize: 13, fontWeight: 600, color: STATUS_COLORS[st] }}>
          {STATUS_LABELS[st]}
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 6 }}>תיאור ההטבה (יוצג למשתמשים, אופציונלי)</div>
        <input className="input" type="text" placeholder='לדוגמה: 🎁 מבצע חגיגי — ללא הגבלה לכולם' value={label} onChange={e => setLabel(e.target.value)} style={{ marginBottom: 0 }} />
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 6 }}>תאריך התחלה (ריק = מיידי)</div>
        <input className="input" type="date" aria-label="תאריך התחלה" value={start} onChange={e => setStart(e.target.value)} style={{ marginBottom: 0 }} />
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 6 }}>תאריך סיום</div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, fontSize: 14 }}>
          <input type="checkbox" checked={noEnd} onChange={e => setNoEnd(e.target.checked)} style={{ width: 16, height: 16 }} />
          ללא תאריך סיום (יישאר פעיל עד ביטול ידני)
        </label>
        {!noEnd && (
          <input className="input" type="date" aria-label="תאריך סיום" value={end} onChange={e => setEnd(e.target.value)} style={{ marginBottom: 0 }} />
        )}
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-success" style={{ flex: 1, marginTop: 0 }} disabled={saving} onClick={() => save(true)}>
          {saving ? '...' : '💾 שמור והפעל לכולם'}
        </button>
        {enabled && (
          <button className="btn" style={{ flex: 1, marginTop: 0, background: 'var(--btn-danger, #c53030)', color: '#fff' }} disabled={saving} onClick={cancelNow}>
            🛑 בטל הטבה מיידית
          </button>
        )}
      </div>
    </div>
  )
}

function GiftAllSection({ onDone }) {
  const [giftType, setGiftType] = useState('searches')
  const [searches, setSearches] = useState(10)
  const [message, setMessage] = useState('')
  const [imageb64, setImageb64] = useState('')
  const [compressing, setCompressing] = useState(false)
  const [sending, setSending] = useState(false)
  const fileRef = useRef(null)

  function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setCompressing(true)
    const reader = new FileReader()
    reader.onload = ev => {
      const img = new Image()
      img.onload = () => {
        const MAX = 800
        const ratio = Math.min(MAX / img.width, MAX / img.height, 1)
        const canvas = document.createElement('canvas')
        canvas.width  = Math.round(img.width  * ratio)
        canvas.height = Math.round(img.height * ratio)
        canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
        setImageb64(canvas.toDataURL('image/jpeg', 0.82))
        setCompressing(false)
      }
      img.src = ev.target.result
    }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  async function send() {
    if (giftType === 'searches' && (!searches || searches < 1)) return
    const preview = giftType === 'monthly'
      ? `להעניק מנוי חופשי חודשי לכל המשתמשים${message.trim() ? ' ולשלוח הודעה' : ''}?`
      : `להוסיף ${searches} חיפושים לכל המשתמשים${message.trim() ? ' ולשלוח הודעה' : ''}?`
    window.Telegram?.WebApp?.showConfirm(preview, async ok => {
      if (!ok) return
      setSending(true)
      try {
        const res = await adminGiftAll(searches, message.trim(), imageb64, giftType)
        const successMsg = giftType === 'monthly'
          ? `🎁 הושלם!\n✅ מנוי חופשי חודשי הוענק לכולם${res.notified ? `\n📤 הודעה נשלחה ל-${res.notified} משתמשים` : ''}`
          : `🎁 הושלם!\n✅ ${searches} חיפושים נוספו לכולם${res.notified ? `\n📤 הודעה נשלחה ל-${res.notified} משתמשים` : ''}`
        window.Telegram?.WebApp?.showAlert(successMsg)
        setMessage('')
        setImageb64('')
        onDone()
      } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
      setSending(false)
    })
  }

  const typeBtn = (type, label) => (
    <button
      type="button"
      onClick={() => setGiftType(type)}
      style={{
        flex: 1, padding: '8px 0', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
        background: giftType === type ? 'var(--button-color, #2196F3)' : 'rgba(0,100,200,0.08)',
        color: giftType === type ? '#fff' : 'var(--hint)',
        transition: 'all 0.15s',
      }}
    >{label}</button>
  )

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
        {typeBtn('searches', '🔢 כמות חיפושים')}
        {typeBtn('monthly', '♾️ מנוי חודשי')}
      </div>

      {giftType === 'searches' && (
        <>
          <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8 }}>כמות חיפושים לכל משתמש:</div>
          <input
            className="input"
            type="number"
            min="1"
            value={searches}
            onChange={e => setSearches(parseInt(e.target.value) || 1)}
            style={{ marginBottom: 10 }}
          />
        </>
      )}

      {giftType === 'monthly' && (
        <div style={{ background: 'rgba(33,150,243,0.1)', border: '1px solid rgba(33,150,243,0.3)', borderRadius: 10, padding: '10px 14px', marginBottom: 10, fontSize: 13, color: 'var(--hint)' }}>
          ♾️ כל המשתמשים יקבלו גישה ללא הגבלת חיפושים ל-30 יום ויצורפו לקבוצת מנויים.
        </div>
      )}

      <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8 }}>הודעה למשתמשים (אופציונלי):</div>
      <textarea
        className="input"
        rows={3}
        placeholder={giftType === 'monthly' ? 'לדוגמה: 🎉 חגיגת שנה! קיבלת מנוי חופשי חודשי' : 'לדוגמה: 🎉 חגיגת שנה! קיבלת 10 חיפושים במתנה'}
        value={message}
        onChange={e => setMessage(e.target.value)}
        style={{ resize: 'vertical', fontFamily: 'inherit', marginBottom: 10 }}
      />
      <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8 }}>תמונה מצורפת (אופציונלי):</div>
      {imageb64 ? (
        <div style={{ position: 'relative', marginBottom: 10 }}>
          <img
            src={imageb64}
            alt="תצוגה מקדימה"
            style={{ width: '100%', height: 140, objectFit: 'cover', borderRadius: 10, display: 'block' }}
          />
          <button
            onClick={() => setImageb64('')}
            style={{
              position: 'absolute', top: 6, left: 6,
              background: 'rgba(0,0,0,0.6)', color: '#fff',
              border: 'none', borderRadius: '50%', width: 28, height: 28,
              fontSize: 14, cursor: 'pointer', lineHeight: 1,
            }}
          >✕</button>
        </div>
      ) : (
        <button
          type="button"
          className="btn btn-secondary"
          style={{ marginTop: 0, marginBottom: 10, fontSize: 13 }}
          disabled={compressing}
          onClick={() => fileRef.current?.click()}
        >
          {compressing ? '⏳ מכווץ...' : '📷 בחר תמונה מהמכשיר'}
        </button>
      )}
      <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFile} />
      <button
        className="btn"
        disabled={sending || (giftType === 'searches' && (!searches || searches < 1))}
        onClick={send}
        style={{ marginTop: 0, background: 'linear-gradient(135deg,#f5a623,#f76b1c)', border: 'none' }}
      >
        {sending ? '⏳ מעבד...' : giftType === 'monthly' ? '🎁 הענק מנוי חודשי לכולם' : `🎁 הענק ${searches || ''} חיפושים לכולם`}
      </button>
    </div>
  )
}

function userStatus(u) {
  if (u.blocked) return { label: 'חסום', color: '#c53030', bg: '#c5303018' }
  if (u.is_subscriber || u.searches_left === -1) return { label: 'מנוי', color: '#0066d6', bg: '#0066d618' }
  if (u.searches_left > 0) return { label: 'חינם', color: '#177a33', bg: '#177a3318' }
  return { label: 'אזל', color: '#975a16', bg: '#975a1618' }
}

function relativeTime(ts) {
  if (!ts) return ''
  try {
    const s = String(ts).replace(' ', 'T')
    const d = new Date(s.includes('+') || s.endsWith('Z') ? s : s + 'Z')
    if (isNaN(d)) return ''
    const diff = (Date.now() - d.getTime()) / 1000
    if (diff < 60)          return 'הרגע'
    if (diff < 3600)        return `לפני ${Math.floor(diff / 60)} דק׳`
    if (diff < 86400)       return `לפני ${Math.floor(diff / 3600)} שע׳`
    if (diff < 2 * 86400)   return 'אתמול'
    if (diff < 7 * 86400)   return `לפני ${Math.floor(diff / 86400)} ימים`
    if (diff < 30 * 86400)  return `לפני ${Math.floor(diff / (7 * 86400))} שב׳`
    return `לפני ${Math.floor(diff / (30 * 86400))} חד׳`
  } catch { return '' }
}

function getInitials(u) {
  if (u.username) return u.username.slice(0, 2).toUpperCase()
  if (u.full_name) {
    const parts = u.full_name.trim().split(/\s+/)
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    return u.full_name.slice(0, 2).toUpperCase()
  }
  return String(u.user_id).slice(-2)
}

function UserCard({ u, expanded, onToggle, onEdit, onMessage, onHistory, onReload }) {
  const [blocking, setBlocking] = useState(false)
  const [togglingConsent, setTogglingConsent] = useState(false)
  const st = userStatus(u)
  const left = u.searches_left === -1 ? '∞' : u.searches_left
  const displayName = u.username ? `@${u.username}` : u.full_name || `id:${u.user_id}`
  const initials = getInitials(u)

  async function toggleBlock(e) {
    e.stopPropagation()
    setBlocking(true)
    try { await adminToggleBlock(u.user_id); onReload() }
    catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setBlocking(false)
  }

  async function toggleConsent(e) {
    e.stopPropagation()
    const isOptedOut = u.broadcast_consent === 0
    const msg = isOptedOut
      ? `להחזיר שידורים ל-${displayName}?`
      : `לבטל שידורים ל-${displayName}?`
    window.Telegram?.WebApp?.showConfirm(msg, async (ok) => {
      if (!ok) return
      setTogglingConsent(true)
      try { await adminToggleBroadcastConsent(u.user_id); onReload() }
      catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
      setTogglingConsent(false)
    })
  }

  return (
    <div className="card" style={{
      padding: 0, overflow: 'hidden', cursor: 'pointer',
      border: u.blocked ? '1px solid #c5303055' : u.is_subscriber ? '1px solid #0066d655' : '1px solid var(--border)',
    }} onClick={() => onToggle(u.user_id)}>
      {/* Collapsed header */}
      <div style={{ display: 'flex', gap: 12, padding: '16px', alignItems: 'center', userSelect: 'none' }}>
        {/* Avatar */}
        <div style={{
          width: 46, height: 46, borderRadius: '50%', flexShrink: 0,
          background: `linear-gradient(135deg, ${st.bg}, ${st.color}22)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16, fontWeight: 800, color: st.color,
          boxShadow: 'inset 0 2px 4px rgba(255,255,255,0.3)',
        }}>
          {initials}
        </div>

        {/* Main info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
            <span style={{
              fontSize: 16, fontWeight: 800, color: 'var(--text-main)', letterSpacing: '-0.2px',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 160,
            }}>{displayName}</span>
            <span style={{
              fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 12, flexShrink: 0,
              background: st.bg, color: st.color, border: `1px solid ${st.color}33`
            }}>{st.label}</span>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', display: 'flex', gap: 8 }}>
            <span>🔍 {u.searches_done} נעשו</span>
            <span>·</span>
            <span style={{ color: u.searches_left === 0 ? '#975a16' : 'var(--text-muted)' }}>{left} נותרו</span>
            {u.last_seen && <><span>·</span><span>{relativeTime(u.last_seen)}</span></>}
          </div>
        </div>

        {/* Chevron */}
        <span style={{ color: 'var(--hint)', fontSize: 14, flexShrink: 0, transition: 'transform 0.2s', display: 'inline-block', transform: expanded ? 'rotate(180deg)' : 'none' }}>▼</span>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div style={{ borderTop: '1px solid var(--border)', padding: '16px', background: 'rgba(0,0,0,0.02)' }} onClick={e => e.stopPropagation()}>

          {/* Stats mini-grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 16 }}>
            {[
              { label: 'נעשו', value: u.searches_done, color: '#0066d6' },
              { label: 'נותרו', value: left, color: st.color },
              { label: 'קוטה', value: u.searches_quota === -1 ? '∞' : u.searches_quota, color: '#0066d6' },
              { label: 'מזהה', value: u.user_id, mono: true },
            ].map(({ label, value, color, mono }) => (
              <div key={label} style={{
                background: 'var(--bg-card)', borderRadius: 12, padding: '10px 6px', textAlign: 'center',
                boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid var(--border)',
              }}>
                <div style={{
                  fontWeight: 800,
                  fontSize: mono ? 11 : 16,
                  color: color || 'var(--text-main)',
                  fontFamily: mono ? 'monospace' : undefined,
                  wordBreak: 'break-all',
                }}>{value}</div>
                <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 2, fontWeight: 500 }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Meta info */}
          <div style={{
            background: 'var(--bg-card)', borderRadius: 16, padding: '12px 16px',
            fontSize: 13, color: 'var(--text-muted)', marginBottom: 16,
            display: 'flex', flexDirection: 'column', gap: 6,
            border: '1px solid var(--border)', boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
          }}>
            {u.member_id != null && (
              <div>🏷 מס׳ חבר: <span style={{ fontFamily: 'monospace', color: 'var(--text-main)', fontWeight: 700 }}>#{u.member_id}</span></div>
            )}
            {u.first_seen && <div>📅 הצטרף: <span style={{ color: 'var(--text-main)', fontWeight: 500 }}>{fmtDateIL(u.first_seen)}</span></div>}
            {u.last_seen  && <div>👁 נראה לאחרונה: <span style={{ color: 'var(--text-main)', fontWeight: 500 }}>{fmtDateTime(u.last_seen)}</span></div>}
            {u.quota_expires && <div>⏰ פג תוקף: <span style={{ color: '#975a16', fontWeight: 700 }}>{u.quota_expires.slice(0, 10)}</span></div>}
            {u.referred_by && <div>🤝 הופנה ע"י: <span style={{ color: '#047857', fontWeight: 700 }}>{u.referred_by}</span></div>}
            {u.channel && <div>📡 ערוץ: <span style={{ color: 'var(--text-main)', fontWeight: 500 }}>{u.channel}</span></div>}
            <div>{u.broadcast_consent === 0 ? '🔕' : '🔔'} שידורים: <span style={{ color: u.broadcast_consent === 0 ? '#c53030' : '#047857', fontWeight: 700 }}>{u.broadcast_consent === 0 ? 'הסכמה בוטלה' : 'פעיל'}</span></div>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <button
              onClick={e => { e.stopPropagation(); onEdit(u) }}
              style={{
                padding: '12px 0', borderRadius: 12, border: '1px solid var(--border)',
                background: 'var(--bg-card)', color: 'var(--text-main)', cursor: 'pointer', fontSize: 14, fontWeight: 700,
                boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
              }}
            >✏️ ערוך תוכנית</button>
            <button
              onClick={e => { e.stopPropagation(); onMessage(u) }}
              style={{
                padding: '12px 0', borderRadius: 12, border: '1px solid var(--border)',
                background: 'var(--bg-card)', color: 'var(--text-main)', cursor: 'pointer', fontSize: 14, fontWeight: 700,
                boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
              }}
            >💬 שלח הודעה</button>
            <button
              onClick={e => { e.stopPropagation(); onHistory(u) }}
              style={{
                padding: '12px 0', borderRadius: 12, border: 'none',
                background: 'rgba(99, 102, 241, 0.1)', color: '#6366f1', cursor: 'pointer', fontSize: 14, fontWeight: 700,
              }}
            >📨 היסטוריית הודעות</button>
            <button
              onClick={toggleBlock}
              disabled={blocking}
              style={{
                padding: '12px 0', borderRadius: 12, border: 'none',
                background: u.blocked ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                color: u.blocked ? '#047857' : '#c53030',
                cursor: blocking ? 'default' : 'pointer', fontSize: 14, fontWeight: 700,
                opacity: blocking ? 0.6 : 1,
              }}
            >{u.blocked ? '🔓 בטל חסימה' : '🚫 חסום משתמש'}</button>
            {u.broadcast_consent === 0 && (
              <button
                onClick={toggleConsent}
                disabled={togglingConsent}
                style={{
                  gridColumn: '1 / -1',
                  padding: '12px 0', borderRadius: 12, border: 'none',
                  background: 'rgba(16, 185, 129, 0.1)', color: '#047857',
                  cursor: togglingConsent ? 'default' : 'pointer', fontSize: 14, fontWeight: 700,
                  opacity: togglingConsent ? 0.6 : 1,
                }}
              >🔔 החזר שידורים למשתמש</button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function ReferralsTab() {
  const [data, setData]       = useState(null)
  const [selected, setSelected] = useState(null)
  const [search, setSearch]   = useState('')

  useEffect(() => {
    adminFetchAllReferrals().then(setData).catch(() => setData({ referrals: [], count: 0, total_bonus: 0 }))
  }, [])

  const filtered = data?.referrals.filter(r => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      r.referrer_name.toLowerCase().includes(q) ||
      r.referee_name.toLowerCase().includes(q) ||
      String(r.referrer_id).includes(q) ||
      String(r.referee_id).includes(q)
    )
  }) ?? []

  if (data === null) return <div className="loading" />

  return (
    <div className="tab-fade-in">
      {/* Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        <div className="card" style={{ padding: '20px', textAlign: 'center', background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.05), transparent)' }}>
          <div style={{ fontSize: 32, fontWeight: 800, color: '#047857', letterSpacing: '-1px' }}>{data.count}</div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 600 }}>סה"כ הפניות מוצלחות</div>
        </div>
        <div className="card" style={{ padding: '20px', textAlign: 'center', background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.05), transparent)' }}>
          <div style={{ fontSize: 32, fontWeight: 800, color: '#0066d6', letterSpacing: '-1px' }}>+{data.total_bonus}</div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 600 }}>חיפושי בונוס חולקו</div>
        </div>
      </div>

      {/* Search */}
      <div style={{ marginBottom: 20, position: 'relative' }}>
        <span style={{ position: 'absolute', right: 14, top: 12, opacity: 0.5 }}>🔍</span>
        <input
          className="input"
          placeholder="חיפוש לפי שם או מזהה (ID)..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ paddingRight: 40, fontSize: 14, height: 46, borderRadius: 16, boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}
        />
      </div>

      {filtered.length === 0 && (
        <div style={{ color: 'var(--hint)', fontSize: 14, textAlign: 'center', padding: 40, background: 'var(--bg-card)', borderRadius: 16, border: '1px dashed var(--border)' }}>
          {search ? 'לא נמצאו תוצאות לחיפוש' : 'אין נתוני הפניות עדיין'}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {filtered.map(ref => (
          <div
            key={ref.id}
            className="card"
            onClick={() => setSelected(ref)}
            style={{
              padding: '16px 20px', cursor: 'pointer', borderRight: '4px solid #047857',
              display: 'flex', alignItems: 'center', gap: 12, transition: 'all 0.2s',
            }}
          >
            <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'rgba(16, 185, 129, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>🤝</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-main)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                <span style={{ color: '#0066d6' }}>{ref.referrer_name}</span>
                <span style={{ color: 'var(--hint)', fontSize: 13, fontWeight: 500 }}>הפנה את</span>
                <span>{ref.referee_name}</span>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                {ref.joined_at?.slice(0, 10)}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{
                background: 'rgba(16, 185, 129, 0.1)', color: '#047857', border: '1px solid rgba(16, 185, 129, 0.2)',
                borderRadius: 20, padding: '4px 12px', fontSize: 13, fontWeight: 800, flexShrink: 0,
              }}>
                +{ref.bonus}
              </span>
              <span style={{ color: 'var(--hint)', fontSize: 18 }}>›</span>
            </div>
          </div>
        ))}
      </div>

      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ padding: '24px' }}>
            <div style={{ fontSize: 18, fontWeight: 800, marginBottom: 20, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: 8 }}>
              🤝 פרטי הפניית חבר
            </div>

            {/* Referrer */}
            <div style={{ background: 'var(--bg)', borderRadius: 16, padding: '16px', marginBottom: 12, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 12, color: '#0066d6', fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>📤 המפנה (קיבל בונוס)</div>
              <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)', marginBottom: 6 }}>{selected.referrer_name}</div>
              <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-muted)' }}>
                <span>מזהה: <b style={{ color: 'var(--text-main)', fontFamily: 'monospace' }}>{selected.referrer_id}</b></span>
                <span>חיפושים: <b style={{ color: '#0066d6' }}>{selected.referrer_searches_left === -1 ? '∞' : selected.referrer_searches_left}</b></span>
              </div>
            </div>

            {/* Bonus */}
            <div style={{
              background: 'rgba(16, 185, 129, 0.05)', border: '1px dashed rgba(16, 185, 129, 0.3)',
              borderRadius: 16, padding: '12px 16px', marginBottom: 12,
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span style={{ fontSize: 14, color: 'var(--text-muted)', fontWeight: 600 }}>🎁 בונוס שהוענק</span>
              <span style={{ fontSize: 20, fontWeight: 800, color: '#047857' }}>+{selected.bonus} חיפושים</span>
            </div>

            {/* Referee */}
            <div style={{ background: 'var(--bg)', borderRadius: 16, padding: '16px', marginBottom: 20, border: '1px solid var(--border)' }}>
              <div style={{ fontSize: 12, color: '#9a4a07', fontWeight: 700, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>📥 המצטרף (הופנה)</div>
              <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)', marginBottom: 6 }}>{selected.referee_name}</div>
              <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-muted)' }}>
                <span>מזהה: <b style={{ color: 'var(--text-main)', fontFamily: 'monospace' }}>{selected.referee_id}</b></span>
                <span>חיפושים: <b style={{ color: '#0066d6' }}>{selected.referee_searches_left === -1 ? '∞' : selected.referee_searches_left}</b></span>
              </div>
            </div>

            <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 20, textAlign: 'center', fontWeight: 500 }}>
              📅 תאריך הצטרפות: {selected.joined_at?.slice(0, 16).replace('T', ' ')}
            </div>

            <button className="btn" onClick={() => setSelected(null)} style={{ width: '100%', height: 48, borderRadius: 12, fontSize: 15, fontWeight: 700, background: 'var(--bg)', border: '1px solid var(--border)' }}>סגור חלונית</button>
          </div>
        </div>
      )}
    </div>
  )
}

function UsersTab() {
  const [users, setUsers]               = useState(null)
  const [filter, setFilter]             = useState('all')
  const [search, setSearch]             = useState('')
  const [sort, setSort]                 = useState('last_seen')
  const [expandedId, setExpandedId]     = useState(null)
  const [editingUser, setEditingUser]   = useState(null)
  const [messagingUser, setMessagingUser] = useState(null)
  const [historyUser, setHistoryUser]   = useState(null)

  function load() { adminFetchUsers().then(setUsers).catch(() => {}) }
  useEffect(() => { load() }, [])
  if (!users) return <div className="loading"></div>

  const FILTERS = [
    ['all',        'הכל',     null],
    ['subscriber', 'מנויים',  'מנוי'],
    ['free',       'חינם',    'חינם'],
    ['empty',      'אזל',     'אזל'],
    ['blocked',    'חסום',    'חסום'],
  ]

  const filtered = users.filter(u => {
    const st = userStatus(u)
    const [, , statusLabel] = FILTERS.find(([id]) => id === filter) || []
    if (statusLabel && st.label !== statusLabel) return false
    if (search) {
      const q = search.toLowerCase()
      const name = (u.username || u.full_name || '').toLowerCase()
      if (!name.includes(q) && !String(u.user_id).includes(q)) return false
    }
    return true
  })

  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'searches_done') return b.searches_done - a.searches_done
    if (sort === 'member_id')     return (b.member_id || 0) - (a.member_id || 0)
    if (!a.last_seen) return 1
    if (!b.last_seen) return -1
    return new Date(b.last_seen) - new Date(a.last_seen)
  })

  const SORTS = [
    ['last_seen',     '🕐 פעיל'],
    ['searches_done', '🔍 חיפושים'],
    ['member_id',     '🏷 מס׳ חבר'],
  ]

  return (
    <div className="tab-fade-in">
      {/* Search */}
      <div style={{ marginBottom: 16, position: 'relative' }}>
        <span style={{ position: 'absolute', right: 14, top: 12, opacity: 0.5 }}>🔍</span>
        <input
          className="input"
          placeholder="חיפוש משתמש לפי שם או ID..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ paddingRight: 40, fontSize: 14, height: 46, borderRadius: 16, boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}
        />
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, overflowX: 'auto', paddingBottom: 8, scrollbarWidth: 'none' }} className="admin-nav-scroll">
        {FILTERS.map(([id, label, statusLabel]) => {
          const count = id === 'all' ? users.length : users.filter(u => userStatus(u).label === statusLabel).length
          return (
            <button key={id} onClick={() => setFilter(id)} style={{
              display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0,
              padding: '8px 16px', borderRadius: 20, border: '1px solid var(--border)',
              background: filter === id ? 'var(--primary)' : 'var(--bg-card)',
              color: filter === id ? '#fff' : 'var(--text-main)',
              cursor: 'pointer', fontWeight: filter === id ? 700 : 500, fontSize: 13,
              boxShadow: filter === id ? '0 4px 12px rgba(0, 122, 255, 0.2)' : '0 1px 3px rgba(0,0,0,0.02)',
              transition: 'all 0.2s',
            }}>
              <span>{label}</span>
              <span style={{ background: filter === id ? 'rgba(255,255,255,0.2)' : 'var(--bg)', color: filter === id ? '#fff' : 'var(--hint)', padding: '2px 8px', borderRadius: 12, fontSize: 11, fontWeight: 800 }}>{count}</span>
            </button>
          )
        })}
      </div>

      {/* Sort + count row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, background: 'var(--bg-card)', padding: '12px 16px', borderRadius: 16, border: '1px solid var(--border)' }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-main)' }}>{sorted.length} תוצאות</span>
        <div style={{ display: 'flex', gap: 6, overflowX: 'auto' }} className="admin-nav-scroll">
          {SORTS.map(([id, label]) => (
            <button key={id} onClick={() => setSort(id)} style={{
              padding: '6px 12px', fontSize: 12, borderRadius: 12, border: 'none', cursor: 'pointer',
              background: sort === id ? 'rgba(0, 122, 255, 0.1)' : 'transparent',
              color: sort === id ? 'var(--primary)' : 'var(--hint)',
              fontWeight: sort === id ? 700 : 500, whiteSpace: 'nowrap',
            }}>{label}</button>
          ))}
        </div>
      </div>

      {sorted.map(u => (
        <UserCard
          key={u.user_id}
          u={u}
          expanded={expandedId === u.user_id}
          onToggle={id => setExpandedId(prev => prev === id ? null : id)}
          onEdit={setEditingUser}
          onMessage={setMessagingUser}
          onHistory={setHistoryUser}
          onReload={load}
        />
      ))}

      {editingUser && (
        <GrantModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onDone={async () => { load(); setEditingUser(null) }}
        />
      )}
      {messagingUser && (
        <SendMessageModal user={messagingUser} onClose={() => setMessagingUser(null)} />
      )}
      {historyUser && (
        <SentMessagesModal user={historyUser} onClose={() => setHistoryUser(null)} />
      )}
    </div>
  )
}

function GrantModal({ user, onClose, onDone }) {
  const [grants, setGrants] = useState(null)
  const [mode, setMode] = useState('grants') // 'grants' | 'custom' | 'watch' | 'history' | 'referrals'
  const [customAmount, setCustomAmount] = useState('')
  const [watchQuotaInput, setWatchQuotaInput] = useState(user.watch_quota != null ? String(user.watch_quota) : '')
  const [saving, setSaving] = useState(false)
  const [history, setHistory] = useState(null)
  const [referralData, setReferralData] = useState(null)
  const [sentMessages, setSentMessages] = useState(null)
  const [pendingGrant, setPendingGrant] = useState(null)

  useEffect(() => { adminFetchGrants().then(setGrants).catch(() => {}) }, [])
  useEffect(() => {
    if (mode === 'history' && history === null) {
      adminFetchUserHistory(user.user_id).then(setHistory).catch(() => setHistory([]))
    }
    if (mode === 'referrals' && referralData === null) {
      adminFetchUserReferrals(user.user_id).then(setReferralData).catch(() => setReferralData({ referrals: [], count: 0, total_bonus: 0 }))
    }
    if (mode === 'messages' && sentMessages === null) {
      adminFetchUserSentMessages(user.user_id).then(setSentMessages).catch(() => setSentMessages([]))
    }
  }, [mode])

  const name = user.username ? `@${user.username}` : user.full_name || `id:${user.user_id}`

  async function grant(searches) {
    setSaving(true)
    try {
      const res = await adminGrantUser(user.user_id, searches)
      window.Telegram?.WebApp?.showAlert(res.msg || '✅ עודכן')
      await onDone()
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה')
    }
    setSaving(false)
  }

  function clickGrant(g) {
    setPendingGrant(prev => prev?.id === g.id ? null : g)
  }

  async function confirmGrant() {
    if (!pendingGrant) return
    if (pendingGrant.searches === 0) {
      window.Telegram?.WebApp?.showConfirm(
        'להסיר את יתרת החיפושים ולהסיר מקבוצת המנויים?',
        async (ok) => { if (ok) { setPendingGrant(null); await grant(0) } }
      )
      return
    }
    setPendingGrant(null)
    await grant(pendingGrant.searches)
  }

  const TABS = [
    ['grants',    '🎁', 'הטבות'],
    ['custom',    '✍️', 'התאמה'],
    ['watch',     '🔔', 'התראות'],
    ['history',   '📋', 'חיפושים'],
    ['referrals', '🤝', 'הפניות'],
    ['messages',  '📨', 'הודעות'],
  ]

  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ padding: '18px 16px' }}>

        {/* Title */}
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, color: 'var(--text)' }}>
          עריכת {name}
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 16, background: 'var(--bg)', borderRadius: 10, padding: 3, overflowX: 'auto', scrollbarWidth: 'none' }}>
          {TABS.map(([id, icon, label]) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              style={{
                flexShrink: 0, minWidth: 52, padding: '6px 8px', fontSize: 10, borderRadius: 7, border: 'none',
                background: mode === id ? 'var(--bg2)' : 'transparent',
                color: mode === id ? 'var(--text)' : 'var(--hint)',
                cursor: 'pointer', fontWeight: mode === id ? 600 : 400,
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2,
                transition: 'all 0.15s',
              }}
            >
              <span style={{ fontSize: 14 }}>{icon}</span>
              <span>{label}</span>
            </button>
          ))}
        </div>

        {mode === 'grants' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {!grants && <div style={{ fontSize: 13, color: 'var(--hint)', textAlign: 'center', padding: 12 }}>⏳</div>}
            {grants && grants.map(g => {
              const selected = pendingGrant?.id === g.id
              return (
                <button
                  key={g.id}
                  disabled={saving}
                  onClick={() => clickGrant(g)}
                  style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 14px', borderRadius: 10,
                    border: selected ? '1px solid #0066d6' : g.searches === 0 ? '1px solid #177a3344' : '1px solid rgba(0,100,200,0.18)',
                    background: selected ? '#0066d622' : g.searches === 0 ? '#177a3311' : 'var(--bg)',
                    cursor: 'pointer', opacity: saving ? 0.5 : 1,
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: 600, color: selected ? '#0066d6' : g.searches === 0 ? '#177a33' : 'var(--text)' }}>{g.label}</span>
                  <span style={{ fontSize: 12, color: selected ? '#0066d6' : 'var(--hint)' }}>{grantTypeLabel(g.searches)}</span>
                </button>
              )
            })}

            {user.is_subscriber && (
              <>
                <div style={{ height: 1, background: 'rgba(0,100,200,0.18)', margin: '4px 0' }} />
                <button
                  disabled={saving}
                  onClick={() => {
                    window.Telegram?.WebApp?.showConfirm('להסיר את המנוי של המשתמש?', async (ok) => {
                      if (!ok) return
                      setSaving(true)
                      try {
                        await adminRevokeSubscription(user.user_id)
                        window.Telegram?.WebApp?.showAlert('✅ המנוי הוסר')
                        await onDone()
                        onClose()
                      } catch {
                        window.Telegram?.WebApp?.showAlert('שגיאה')
                      }
                      setSaving(false)
                    })
                  }}
                  style={{
                    display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 6,
                    padding: '10px 14px', borderRadius: 10,
                    border: '1px solid #c5303044',
                    background: '#c5303011', cursor: 'pointer', opacity: saving ? 0.5 : 1,
                  }}
                >
                  <span style={{ fontSize: 13, color: '#c53030', fontWeight: 600 }}>🚫 הסר מנוי</span>
                </button>
              </>
            )}
          </div>
        )}

        {mode === 'custom' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <input
              className="input"
              type="number" min="1"
              placeholder="כמות חיפושים להוסיף"
              value={customAmount}
              onChange={e => setCustomAmount(e.target.value)}
              style={{ fontSize: 13 }}
            />
            <button
              disabled={saving || !customAmount || parseInt(customAmount) < 1}
              onClick={() => grant(parseInt(customAmount))}
              style={{
                padding: '10px', borderRadius: 10, border: 'none',
                background: 'var(--accent)', color: '#fff', fontSize: 13,
                fontWeight: 600, cursor: 'pointer', opacity: (saving || !customAmount) ? 0.5 : 1,
              }}
            >{saving ? '...' : 'הוסף'}</button>
          </div>
        )}

        {mode === 'watch' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 12, color: 'var(--hint)' }}>
              מגבלת התראות יד2 עבור משתמש זה.<br/>
              ריק = השתמש במגבלה הגלובלית מהגדרות הפיצ'רים.
            </div>
            <input
              className="input"
              type="number" min="0" max="50"
              placeholder="מגבלה אישית (ריק = גלובלי)"
              value={watchQuotaInput}
              onChange={e => setWatchQuotaInput(e.target.value)}
              style={{ fontSize: 13 }}
            />
            <button
              disabled={saving}
              onClick={async () => {
                setSaving(true)
                try {
                  const val = watchQuotaInput.trim() === '' ? null : parseInt(watchQuotaInput)
                  await adminSetWatchQuota(user.user_id, val)
                  window.Telegram?.WebApp?.showAlert(val === null ? '✅ אופס לברירת המחדל' : `✅ הוגדרו ${val} התראות`)
                  await onDone()
                } catch {
                  window.Telegram?.WebApp?.showAlert('שגיאה')
                }
                setSaving(false)
              }}
              style={{
                padding: '10px', borderRadius: 10, border: 'none',
                background: 'var(--accent)', color: '#fff', fontSize: 13,
                fontWeight: 600, cursor: 'pointer', opacity: saving ? 0.5 : 1,
              }}
            >{saving ? '...' : '💾 שמור'}</button>
            {user.watch_quota != null && (
              <div style={{ fontSize: 11, color: 'var(--hint)', textAlign: 'center' }}>
                מגבלה נוכחית: {user.watch_quota} התראות (אישי)
              </div>
            )}
          </div>
        )}

        {mode === 'history' && (
          <div>
            {history === null && <div className="loading"></div>}
            {history !== null && history.length === 0 && (
              <div style={{ color: 'var(--hint)', fontSize: 13, textAlign: 'center', padding: 12 }}>
                אין היסטוריית חיפושים
              </div>
            )}
            {history !== null && history.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ fontSize: 11, color: 'var(--hint)', marginBottom: 2 }}>{history.length} חיפושים אחרונים</div>
                {history.map((item, i) => (
                  <div key={i} style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    background: 'var(--bg)', borderRadius: 8, padding: '7px 10px',
                  }}>
                    <span style={{
                      background: '#f5c518', color: '#111', fontWeight: 700,
                      borderRadius: 6, padding: '3px 10px', fontSize: 13, letterSpacing: 1,
                    }}>
                      {item.plate ?? item}
                    </span>
                    {item.searched_at && (
                      <span style={{ fontSize: 11, color: 'var(--hint)' }}>
                        {item.searched_at.slice(0, 16).replace('T', ' ')}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {mode === 'referrals' && (
          <div>
            {referralData === null && <div className="loading"></div>}
            {referralData !== null && (
              <>
                {/* Summary */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                  <div style={{ background: 'var(--bg)', borderRadius: 8, padding: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: 20, fontWeight: 700 }}>{referralData.count}</div>
                    <div style={{ fontSize: 11, color: 'var(--hint)' }}>הצטרפו</div>
                  </div>
                  <div style={{ background: 'var(--bg)', borderRadius: 8, padding: '8px', textAlign: 'center' }}>
                    <div style={{ fontSize: 20, fontWeight: 700 }}>{referralData.total_bonus}</div>
                    <div style={{ fontSize: 11, color: 'var(--hint)' }}>חיפושים הרוויח</div>
                  </div>
                </div>
                {/* Note */}
                <div style={{ fontSize: 11, color: 'var(--hint)', marginBottom: 8, padding: '6px 8px', background: 'var(--bg)', borderRadius: 6 }}>
                  ℹ️ מוצגים רק משתמשים שהצטרפו בפועל דרך הלינק. לא ניתן לדעת מי קיבל את הלינק ולא הצטרף.
                </div>
                {referralData.referrals.length === 0 && (
                  <div style={{ color: 'var(--hint)', fontSize: 13, textAlign: 'center', padding: 12 }}>
                    אין הפניות עדיין
                  </div>
                )}
                {referralData.referrals.map(ref => (
                  <div key={ref.id} style={{
                    display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px',
                    background: 'var(--bg)', borderRadius: 8, marginBottom: 6,
                    borderRight: '3px solid #177a33',
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{ref.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--hint)' }}>{ref.joined_at?.slice(0, 10)}</div>
                    </div>
                    <span style={{
                      background: '#177a3320', color: '#177a33',
                      borderRadius: 20, padding: '3px 9px', fontSize: 11, fontWeight: 700, flexShrink: 0,
                    }}>
                      ✅ +{ref.bonus}
                    </span>
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {mode === 'messages' && (
          <div>
            {sentMessages === null && <div className="loading"></div>}
            {sentMessages !== null && sentMessages.length === 0 && (
              <div style={{ color: 'var(--hint)', fontSize: 13, textAlign: 'center', padding: 12 }}>
                אין הודעות מערכת
              </div>
            )}
            {sentMessages !== null && sentMessages.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {sentMessages.map(msg => {
                  const kindColors = {
                    grant:           { bg: '#0066d618', border: '#0066d655', icon: '🎁' },
                    referral_bonus:  { bg: '#177a3318', border: '#177a3355', icon: '🤝' },
                    referral_info:   { bg: '#9a4a0718', border: '#9a4a0755', icon: 'ℹ️' },
                    payment:         { bg: '#16a34a18', border: '#16a34a55', icon: '💳' },
                    broadcast:       { bg: '#0066d618', border: '#0066d655', icon: '📢' },
                    expiry_reminder: { bg: '#9a4a0718', border: '#9a4a0755', icon: '⏰' },
                    block:           { bg: '#c5303018', border: '#c5303055', icon: '🚫' },
                    unblock:         { bg: '#177a3318', border: '#177a3355', icon: '✅' },
                    ticket_reply:    { bg: '#6366f118', border: '#6366f155', icon: '💬' },
                    admin_dm:        { bg: '#ec489918', border: '#ec489955', icon: '✉️' },
                    welcome:         { bg: '#0066d618', border: '#0066d655', icon: '👋' },
                    promo_welcome:   { bg: '#9a4a0718', border: '#9a4a0755', icon: '🎉' },
                    code_applied:    { bg: '#0066d618', border: '#0066d655', icon: '🔑' },
                    watch_alert:     { bg: '#6366f118', border: '#6366f155', icon: '🔔' },
                  }
                  const style = kindColors[msg.kind] || { bg: 'var(--bg)', border: 'rgba(0,100,200,0.18)', icon: '📩' }
                  return (
                    <div key={msg.id} style={{
                      background: style.bg, border: `1px solid ${style.border}`,
                      borderRadius: 10, padding: '10px 12px',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                        <span style={{ fontSize: 11, color: 'var(--hint)' }}>{style.icon} {msg.kind}</span>
                        <span style={{ fontSize: 10, color: 'var(--hint)' }}>{msg.sent_at?.slice(0, 16).replace('T', ' ')}</span>
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text)', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                        {msg.text.replace(/\\/g, '').replace(/\*/g, '')}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          {pendingGrant && (
            <button
              className="btn"
              disabled={saving}
              onClick={confirmGrant}
              style={{ flex: 1, marginTop: 0 }}
            >
              {saving ? '⏳...' : '✅ אשר הטבה'}
            </button>
          )}
          <button
            className="btn btn-secondary"
            onClick={onClose}
            style={{ flex: pendingGrant ? 1 : undefined, marginTop: 0 }}
          >
            ביטול
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

function SendMessageModal({ user, onClose }) {
  const [message, setMessage] = useState('')
  const [sending, setSending] = useState(false)
  const name = user.username ? `@${user.username}` : user.full_name || `id:${user.user_id}`

  async function send() {
    if (!message.trim()) return
    setSending(true)
    try {
      const res = await adminSendUserMessage(user.user_id, message.trim())
      window.Telegram?.WebApp?.showAlert(res.ok ? '✅ נשלח בהצלחה' : '❌ שליחה נכשלה')
      if (res.ok) onClose()
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה בשליחה')
    }
    setSending(false)
  }

  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">💬 הודעה ל{name}</div>
        <textarea
          className="input"
          rows={4}
          placeholder="כתוב הודעה..."
          value={message}
          onChange={e => setMessage(e.target.value)}
          style={{ resize: 'vertical', fontFamily: 'inherit' }}
        />
        <button className="btn" disabled={sending || !message.trim()} onClick={send}>
          {sending ? '⏳ שולח...' : '📤 שלח'}
        </button>
        <button className="btn btn-secondary" style={{ marginTop: 6 }} onClick={onClose}>ביטול</button>
      </div>
    </div>,
    document.body
  )
}

function SentMessagesModal({ user, onClose }) {
  const [msgs, setMsgs] = useState(null)
  const name = user.username ? `@${user.username}` : user.full_name || `id:${user.user_id}`

  useEffect(() => {
    adminFetchUserSentMessages(user.user_id).then(setMsgs).catch(() => setMsgs([]))
  }, [user.user_id])

  const kindMeta = {
    grant:           { icon: '🎁', label: 'הטבה', color: '#0066d6' },
    payment:         { icon: '💳', label: 'תשלום', color: '#177a33' },
    broadcast:       { icon: '📢', label: 'שידור', color: '#0066d6' },
    expiry_reminder: { icon: '⏰', label: 'תזכורת מנוי', color: '#9a4a07' },
    block:           { icon: '🚫', label: 'חסימה', color: '#c53030' },
    ticket_reply:    { icon: '💬', label: 'טיקט', color: '#6366f1' },
    admin_dm:        { icon: '✉️', label: 'הודעת מנהל', color: '#ec4899' },
  }

  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ padding: '18px 16px' }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14 }}>📨 הודעות מערכת — {name}</div>
        {msgs === null && <div className="loading"></div>}
        {msgs !== null && msgs.length === 0 && (
          <div style={{ color: 'var(--hint)', fontSize: 13, textAlign: 'center', padding: 20 }}>אין הודעות מערכת</div>
        )}
        {msgs !== null && msgs.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {msgs.map(msg => {
              const m = kindMeta[msg.kind] || { icon: '📩', label: msg.kind, color: 'var(--hint)' }
              return (
                <div key={msg.id} style={{
                  background: 'var(--bg)', borderRadius: 10, padding: '10px 12px',
                  borderRight: `3px solid ${m.color}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: m.color }}>{m.icon} {m.label}</span>
                    <span style={{ fontSize: 10, color: 'var(--hint)' }}>{msg.sent_at?.slice(0, 16).replace('T', ' ')}</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text)', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                    {msg.text.replace(/\\/g, '').replace(/\*/g, '')}
                  </div>
                </div>
              )
            })}
          </div>
        )}
        <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={onClose}>סגור</button>
      </div>
    </div>,
    document.body
  )
}

function PaymentMethodsTab() {
  const [methods, setMethods] = useState(null)
  const [editingMethod, setEditingMethod] = useState(null)
  const [showAdd, setShowAdd] = useState(false)
  const [confirmId, setConfirmId] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState('')
  const [loadFailed, setLoadFailed] = useState(false)

  function load() {
    setLoadFailed(false)
    adminFetchPaymentMethods()
      .then(r => setMethods(Array.isArray(r) ? r : []))
      .catch(() => { setMethods([]); setLoadFailed(true) })
  }
  useEffect(() => { load() }, [])

  function fail(msg) {
    setError(msg)
    window.Telegram?.WebApp?.showAlert?.(msg)
  }

  async function deleteMethod(id) {
    setBusyId(id); setError('')
    try { await adminDeletePaymentMethod(id); setConfirmId(null); load() }
    catch { fail('המחיקה נכשלה, נסו שוב') }
    setBusyId(null)
  }

  async function toggleActive(m) {
    setBusyId(m.id); setError('')
    try {
      await adminUpdatePaymentMethod(m.id, { name: m.name, logo_url: m.logo_url, payment_url: m.payment_url, active: !m.active, requires_manual_approval: m.requires_manual_approval })
      load()
    } catch { fail('העדכון נכשל, נסו שוב') }
    setBusyId(null)
  }

  if (!methods) return <div className="loading"></div>

  const actionBtn = { margin: 0, width: '100%', minHeight: 44, padding: '0 10px', borderRadius: 12, fontSize: 14, fontWeight: 700 }
  const list = methods.filter(Boolean)

  return (
    <div className="tab-fade-in">
      <div className="card" style={{ padding: 16, marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span aria-hidden="true" style={{ width: 44, height: 44, borderRadius: 12, background: 'rgba(0, 122, 255, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, flexShrink: 0 }}>💳</span>
          <div style={{ minWidth: 0 }}>
            <h2 style={{ margin: 0, fontWeight: 800, fontSize: 18, color: 'var(--text-main)' }}>אמצעי תשלום</h2>
            <div style={{ fontSize: 13, color: 'var(--text-main)', opacity: 0.8, marginTop: 2 }}>ניהול שיטות התשלום ללקוחות</div>
          </div>
        </div>
        <button type="button" className="btn" onClick={() => setShowAdd(true)} style={{ margin: '14px 0 0', minHeight: 48, padding: '0 16px', borderRadius: 14, fontSize: 15 }}>
          <span aria-hidden="true">➕ </span>הוסף אמצעי תשלום
        </button>
      </div>

      {error && (
        <div role="alert" style={{ marginBottom: 12, padding: '10px 14px', borderRadius: 12, background: '#fee2e2', color: '#991b1b', fontSize: 14, fontWeight: 600 }}>{error}</div>
      )}

      {loadFailed && (
        <div role="alert" className="card" style={{ padding: 16, marginBottom: 16, textAlign: 'center' }}>
          <div style={{ fontSize: 14, color: 'var(--text-main)', marginBottom: 10 }}>לא הצלחנו לטעון את אמצעי התשלום</div>
          <button type="button" className="btn btn-secondary" style={{ ...actionBtn, width: 'auto', padding: '0 24px' }} onClick={load}>נסו שוב</button>
        </div>
      )}

      {!loadFailed && list.length === 0 && (
        <div style={{ color: 'var(--text-main)', fontSize: 14, textAlign: 'center', padding: 32, background: 'var(--bg-card)', borderRadius: 16, border: '1px dashed var(--border)' }}>
          עדיין אין אמצעי תשלום. הוסיפו את הראשון כדי שלקוחות יוכלו לשלם.
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 300px), 1fr))', gap: 12 }}>
        {list.map(m => {
          const busy = busyId === m.id
          const confirming = confirmId === m.id
          return (
            <div key={m.id} className="card" style={{ padding: 16, margin: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {m.logo_url
                  ? <img src={m.logo_url} alt="" width={48} height={48} style={{ width: 48, height: 48, objectFit: 'contain', borderRadius: 12, background: '#fff', padding: 6, border: '1px solid var(--border)', flexShrink: 0, filter: m.active ? 'none' : 'grayscale(1)' }} onError={e => { e.currentTarget.style.visibility = 'hidden' }} />
                  : <div aria-hidden="true" style={{ width: 48, height: 48, borderRadius: 12, background: 'var(--bg)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, flexShrink: 0 }}>💳</div>
                }
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)', overflowWrap: 'anywhere', lineHeight: 1.25 }}>{m.name}</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
                    <span style={{
                      fontSize: 12, fontWeight: 700, padding: '2px 10px', borderRadius: 12,
                      background: m.active ? '#dcfce7' : '#fee2e2', color: m.active ? '#166534' : '#991b1b',
                    }}>{m.active ? '✓ פעיל' : '⏸ מושבת'}</span>
                    {m.requires_manual_approval && (
                      <span style={{ fontSize: 12, fontWeight: 700, padding: '2px 10px', borderRadius: 12, background: 'var(--bg)', color: 'var(--text-main)', border: '1px solid var(--border)' }}>✋ דורש אישור ידני</span>
                    )}
                  </div>
                </div>
              </div>

              {m.payment_url
                ? <div dir="ltr" title={m.payment_url} style={{ marginTop: 12, padding: '8px 12px', borderRadius: 10, background: 'var(--bg)', color: 'var(--text-main)', fontSize: 13, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', userSelect: 'text', WebkitUserSelect: 'text', unicodeBidi: 'isolate' }}>{m.payment_url}</div>
                : <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 10, background: 'var(--bg)', color: 'var(--text-main)', fontSize: 13 }}>ללא קישור (תשלום ידני)</div>
              }

              {confirming ? (
                <div role="group" aria-label={`אישור מחיקת ${m.name}`} style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)', marginBottom: 8, overflowWrap: 'anywhere' }}>למחוק את "{m.name}"? אי אפשר לבטל.</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <button type="button" className="btn" disabled={busy} onClick={() => deleteMethod(m.id)} style={{ ...actionBtn, background: '#c53030', boxShadow: 'none' }}>{busy ? '⏳...' : 'כן, מחק'}</button>
                    <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => setConfirmId(null)} style={actionBtn}>ביטול</button>
                  </div>
                </div>
              ) : (
                <>
                  <button
                    type="button" role="switch" aria-checked={!!m.active} disabled={busy} onClick={() => toggleActive(m)}
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, width: '100%', marginTop: 12, minHeight: 48, padding: '0 14px', textAlign: 'start', fontFamily: 'inherit', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, color: 'var(--text-main)', cursor: 'pointer', opacity: busy ? 0.6 : 1 }}
                  >
                    <span style={{ minWidth: 0 }}>
                      <span style={{ display: 'block', fontSize: 14, fontWeight: 700 }}>{m.active ? 'מוצג ללקוחות' : 'מוסתר מלקוחות'}</span>
                    </span>
                    <span aria-hidden="true" style={{ width: 44, height: 24, borderRadius: 12, flexShrink: 0, position: 'relative', background: m.active ? '#177a33' : '#6e6e73', transition: 'background 0.2s' }}>
                      <span style={{ position: 'absolute', top: 3, width: 18, height: 18, borderRadius: '50%', background: '#fff', transition: 'inset-inline-start 0.2s', insetInlineStart: m.active ? 23 : 3 }} />
                    </span>
                  </button>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
                    <button type="button" className="btn btn-secondary" onClick={() => setEditingMethod(m)} aria-label={`עריכה: ${m.name}`} style={{ ...actionBtn, border: '1px solid var(--border)' }}>
                      <span aria-hidden="true">✏️ </span>עריכה
                    </button>
                    <button type="button" className="btn btn-secondary" onClick={() => { setError(''); setConfirmId(m.id) }} aria-label={`מחיקה: ${m.name}`} style={{ ...actionBtn, color: '#c53030', border: '1px solid #c53030' }}>
                      <span aria-hidden="true">🗑️ </span>מחיקה
                    </button>
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>

      {(showAdd || editingMethod) && (
        <PaymentMethodModal
          method={editingMethod}
          onClose={() => { setShowAdd(false); setEditingMethod(null) }}
          onSaved={() => { load(); setShowAdd(false); setEditingMethod(null) }}
        />
      )}
    </div>
  )
}

function PaymentMethodModal({ method, onClose, onSaved }) {
  const [name, setName]             = useState(method?.name || '')
  const [logoUrl, setLogoUrl]       = useState(method?.logo_url || '')
  const [paymentUrl, setPaymentUrl] = useState(method?.payment_url || '')
  const [manual, setManual]         = useState(method ? method.requires_manual_approval : true)
  const [uploading, setUploading]   = useState(false)
  const [saving, setSaving]         = useState(false)
  const fileRef = useRef()

  async function handleLogoFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const res = await adminUploadLogo(file)
      setLogoUrl(res.url)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה בהעלאת הלוגו') }
    setUploading(false)
  }

  async function save() {
    if (!name.trim()) return
    setSaving(true)
    try {
      if (method) {
        await adminUpdatePaymentMethod(method.id, { name: name.trim(), logo_url: logoUrl, payment_url: paymentUrl.trim(), active: method.active, requires_manual_approval: manual })
      } else {
        await adminAddPaymentMethod(name.trim(), logoUrl, paymentUrl.trim(), manual)
      }
      onSaved()
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  return (
    <Sheet title={method ? `✏️ עריכת ${method.name}` : '➕ אמצעי תשלום חדש'} onClose={onClose} footer={<>
      <button className="btn" disabled={saving || uploading || !name.trim()} onClick={save}>{saving ? '⏳...' : '💾 שמור'}</button>
      <button className="btn btn-secondary" onClick={onClose}>ביטול</button>
    </>}>
      <Field label="שם">
        <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder="לדוגמה: PayPal" />
      </Field>

      <FieldGroup label="לוגו">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {logoUrl
            ? <img src={logoUrl} alt="" width={52} height={52} style={{ width: 52, height: 52, objectFit: 'contain', borderRadius: 10, background: '#fff', border: '1px solid var(--border)', padding: 4, flexShrink: 0 }} onError={e => e.target.style.display='none'} />
            : <div aria-hidden="true" style={{ width: 52, height: 52, borderRadius: 10, background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, flexShrink: 0 }}>💳</div>
          }
          <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleLogoFile} aria-label="העלאת לוגו" />
            <button type="button" className="btn btn-secondary" style={{ margin: 0, minHeight: 44, padding: 10, fontSize: 14 }}
              onClick={() => fileRef.current?.click()} disabled={uploading}
            >{uploading ? '⏳ מעלה...' : '📁 בחר תמונה'}</button>
            {logoUrl && (
              <button type="button" className="btn btn-danger" style={{ margin: 0, minHeight: 44, padding: 10, fontSize: 14 }} onClick={() => setLogoUrl('')}>הסר לוגו</button>
            )}
          </div>
        </div>
      </FieldGroup>

      <Field label="כתובת לתשלום (URL)">
        <input className="input" dir="ltr" value={paymentUrl} onChange={e => setPaymentUrl(e.target.value)} placeholder="https://..." />
      </Field>

      <button
        type="button" role="switch" aria-checked={manual}
        onClick={() => setManual(v => !v)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, width: '100%', textAlign: 'start', fontFamily: 'inherit',
          background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, padding: '10px 14px', minHeight: 56, cursor: 'pointer', color: 'var(--text-main)',
        }}
      >
        <span style={{ minWidth: 0 }}>
          <span style={{ display: 'block', fontSize: 14, fontWeight: 700 }}>אישור ידני</span>
          <span style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)' }}>{manual ? 'מנהל מאשר ידנית לאחר קבלת תשלום' : 'אישור אוטומטי מיידי (כגון PayPal API)'}</span>
        </span>
        <span aria-hidden="true" style={{
          width: 44, height: 24, borderRadius: 12, transition: 'background 0.2s', flexShrink: 0,
          background: manual ? '#c53030' : '#177a33', position: 'relative',
        }}>
          <span style={{
            position: 'absolute', top: 3, width: 18, height: 18, borderRadius: '50%', background: '#fff',
            transition: 'left 0.2s', left: manual ? 3 : 23,
          }} />
        </span>
      </button>
    </Sheet>
  )
}

function PromoTab() {
  const [settings, setSettings]               = useState(null)
  const [saving, setSaving]                   = useState(false)
  const [promoSearches, setPromoSearches]     = useState('0')
  const [promoUnlimited, setPromoUnlimited]   = useState(false)
  const [promoNoEnd, setPromoNoEnd]           = useState(false)
  const [promoStart, setPromoStart]           = useState('')
  const [promoEnd, setPromoEnd]               = useState('')
  const [promoDurationDays, setPromoDurationDays] = useState('30')
  const [promoIsSubscriber, setPromoIsSubscriber] = useState(false)
  const [promoLabel, setPromoLabel]           = useState('')
  const [promoPackages, setPromoPackages]     = useState(null)

  useEffect(() => {
    adminFetchPackages().then(setPromoPackages).catch(() => setPromoPackages([]))
    adminFetchSettings().then(s => {
      setSettings(s)
      const ps = s.promo_searches ?? 0
      setPromoUnlimited(ps === -1)
      setPromoSearches(ps === -1 ? '' : String(ps))
      setPromoStart(s.promo_start || '')
      setPromoEnd(s.promo_end || '')
      setPromoNoEnd(!s.promo_end)
      setPromoDurationDays(String(s.promo_duration_days ?? 30))
      setPromoIsSubscriber(!!s.promo_is_subscriber)
      setPromoLabel(s.promo_label || '')
    }).catch(() => {})
  }, [])

  async function savePromo() {
    setSaving(true)
    try {
      const ps  = promoUnlimited ? -1 : (parseInt(promoSearches) || 0)
      const dur = parseInt(promoDurationDays) || 0
      await adminUpdateSettings({
        promo_searches:      ps,
        promo_start:         promoStart,
        promo_end:           promoNoEnd ? '' : promoEnd,
        promo_duration_days: dur,
        promo_is_subscriber: promoIsSubscriber,
        promo_label:         promoLabel,
      })
      setSettings(s => ({
        ...s,
        promo_searches: ps, promo_start: promoStart,
        promo_end: promoNoEnd ? '' : promoEnd,
        promo_duration_days: dur,
        promo_is_subscriber: promoIsSubscriber,
        promo_label: promoLabel,
      }))
      window.Telegram?.WebApp?.showAlert('✅ מבצע עודכן')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function clearPromo() {
    setSaving(true)
    try {
      await adminUpdateSettings({
        promo_searches: 0, promo_start: '', promo_end: '',
        promo_duration_days: 30, promo_is_subscriber: false, promo_label: '',
      })
      setSettings(s => ({ ...s, promo_searches: 0, promo_start: '', promo_end: '', promo_duration_days: 30, promo_is_subscriber: false, promo_label: '' }))
      setPromoSearches('0'); setPromoUnlimited(false); setPromoStart(''); setPromoEnd('')
      setPromoNoEnd(false); setPromoDurationDays('30'); setPromoIsSubscriber(false); setPromoLabel('')
      window.Telegram?.WebApp?.showAlert('✅ המבצע בוטל')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  function promoStatus() {
    if (!settings) return null
    const ps = settings.promo_searches ?? 0
    if (ps === 0) return null
    const today = new Date().toISOString().slice(0, 10)
    const start = settings.promo_start || ''
    const end   = settings.promo_end   || ''
    const startOk = !start || today >= start
    const endOk   = !end   || today <= end
    if (startOk && endOk) return 'active'
    if (start && today < start) return 'upcoming'
    return 'expired'
  }

  if (!settings) return <div className="loading"></div>

  const STATUS_COLORS = { active: '#177a33', upcoming: '#975a16', expired: '#c53030' }
  const STATUS_LABELS = { active: '🟢 פעיל כעת', upcoming: '🟡 טרם התחיל', expired: '🔴 הסתיים' }
  const pStatus = promoStatus()

  return (
    <div className="tab-fade-in">
      <div className="card" style={{ padding: '20px', marginBottom: 24, background: 'linear-gradient(135deg, rgba(236, 72, 153, 0.05), transparent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 24 }}>🎉</span>
            <div>
              <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>מבצע הצטרפות משתמשים</div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>ניהול קמפיין הטבות ללקוחות חדשים</div>
            </div>
          </div>
          {pStatus && (
            <span style={{
              fontSize: 13, fontWeight: 800, padding: '4px 12px', borderRadius: 12,
              background: `${STATUS_COLORS[pStatus]}20`, color: STATUS_COLORS[pStatus], border: `1px solid ${STATUS_COLORS[pStatus]}40`
            }}>
              {STATUS_LABELS[pStatus]}
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 16 }}>
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: 'var(--primary)' }}>1️⃣</span> הגדרת ההטבה ללקוח
          </div>
          
          {promoPackages && promoPackages.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 10 }}>בחר חבילה מוגדרת במערכת:</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {promoPackages.map(pkg => {
                  const isMatch = pkg.searches === -1
                    ? promoUnlimited
                    : (!promoUnlimited && String(pkg.searches) === promoSearches)
                  return (
                    <button
                      key={pkg.id}
                      onClick={() => {
                        if (pkg.searches === -1) { setPromoUnlimited(true); setPromoSearches('') }
                        else { setPromoUnlimited(false); setPromoSearches(String(pkg.searches)) }
                        setPromoLabel(pkg.label || '')
                      }}
                      style={{
                        padding: '8px 16px', borderRadius: 12, fontSize: 13, fontWeight: 700,
                        border: isMatch ? '2px solid var(--primary)' : '1px solid var(--border)',
                        background: isMatch ? 'var(--primary)' : 'var(--bg-card)',
                        color: isMatch ? '#fff' : 'var(--text-main)',
                        cursor: 'pointer', transition: 'all 0.2s',
                        boxShadow: isMatch ? '0 4px 12px rgba(0, 122, 255, 0.2)' : 'none'
                      }}
                    >
                      {pkg.label}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 10 }}>או הגדר תוכנית כללית:</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
            {[
              { label: '♾️ ללא הגבלה לצמיתות', searches: -2 },
              { label: '📅 מנוי חודשי (30 יום)', searches: -1 },
            ].map(opt => (
              <button
                key={opt.searches}
                onClick={() => { setPromoUnlimited(true); setPromoSearches(''); setPromoLabel(opt.label) }}
                style={{
                  padding: '8px 16px', borderRadius: 12, fontSize: 13, fontWeight: 700,
                  border: (promoUnlimited && promoLabel === opt.label) ? '2px solid var(--primary)' : '1px solid var(--border)',
                  background: (promoUnlimited && promoLabel === opt.label) ? 'var(--primary)' : 'var(--bg-card)',
                  color: (promoUnlimited && promoLabel === opt.label) ? '#fff' : 'var(--text-main)',
                  cursor: 'pointer', transition: 'all 0.2s',
                  boxShadow: (promoUnlimited && promoLabel === opt.label) ? '0 4px 12px rgba(0, 122, 255, 0.2)' : 'none'
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 16, alignItems: 'center', background: 'var(--bg)', padding: '12px 16px', borderRadius: 12, border: '1px solid var(--border)' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 14, fontWeight: 700, cursor: 'pointer', color: promoUnlimited ? 'var(--text-main)' : 'var(--text-muted)' }}>
              <div style={{ width: 20, height: 20, borderRadius: 6, border: `2px solid ${promoUnlimited ? 'var(--primary)' : 'var(--border)'}`, background: promoUnlimited ? 'var(--primary)' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {promoUnlimited && <span style={{ color: '#fff', fontSize: 12 }}>✓</span>}
              </div>
              <input type="checkbox" checked={promoUnlimited} onChange={e => setPromoUnlimited(e.target.checked)} style={{ display: 'none' }} />
              ללא הגבלת חיפושים במערכת
            </label>
            {!promoUnlimited && (
              <div style={{ flex: 1 }}>
                <input className="input" type="number" min="0" placeholder="או הגדר כמות (0 לביטול)..." value={promoSearches} onChange={e => setPromoSearches(e.target.value)} style={{ margin: 0, height: 40, borderRadius: 10 }} />
              </div>
            )}
          </div>
        </div>

        <div className="card" style={{ padding: '20px' }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: '#0066d6' }}>2️⃣</span> פרטי הקמפיין להצגה
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 16 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 14, fontWeight: 600, cursor: 'pointer', background: 'var(--bg)', padding: '16px', borderRadius: 12, border: '1px solid var(--border)' }}>
              <div style={{ width: 20, height: 20, borderRadius: 6, border: `2px solid ${promoIsSubscriber ? '#047857' : 'var(--border)'}`, background: promoIsSubscriber ? '#047857' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {promoIsSubscriber && <span style={{ color: '#fff', fontSize: 12 }}>✓</span>}
              </div>
              <input type="checkbox" checked={promoIsSubscriber} onChange={e => setPromoIsSubscriber(e.target.checked)} style={{ display: 'none' }} />
              <span>הוסף את המשתמשים אוטומטית לקבוצת <b style={{ color: '#047857' }}>מנויים פעילים</b></span>
            </label>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>תוקף ההטבה מיום ההצטרפות (בימים, 0=לצמיתות)</div>
                <input className="input" type="number" min="0" placeholder="לדוגמה: 30" value={promoDurationDays} onChange={e => setPromoDurationDays(e.target.value)} style={{ margin: 0, borderRadius: 10 }} />
              </div>
              <div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>תיאור ההטבה המוצג בהודעת המערכת</div>
                <input className="input" type="text" placeholder='לדוגמה: ♾️ גישה חופשית' value={promoLabel} onChange={e => setPromoLabel(e.target.value)} style={{ margin: 0, borderRadius: 10 }} />
              </div>
            </div>
          </div>
        </div>

        <div className="card" style={{ padding: '20px' }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: '#9a4a07' }}>3️⃣</span> תאריכי תוקף למבצע
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 6 }}>תאריך התחלת המבצע</div>
              <input className="input" type="date" aria-label="תאריך התחלה" value={promoStart} onChange={e => setPromoStart(e.target.value)} style={{ margin: 0, borderRadius: 10 }} />
            </div>
            
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 600 }}>תאריך סיום המבצע</div>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, cursor: 'pointer', color: promoNoEnd ? 'var(--primary)' : 'var(--text-muted)' }}>
                  <input type="checkbox" checked={promoNoEnd} onChange={e => setPromoNoEnd(e.target.checked)} style={{ margin: 0 }} />
                  ללא תאריך תפוגה
                </label>
              </div>
              {!promoNoEnd ? (
                <input className="input" type="date" aria-label="תאריך סיום" value={promoEnd} onChange={e => setPromoEnd(e.target.value)} style={{ margin: 0, borderRadius: 10 }} />
              ) : (
                <div style={{ height: 46, background: 'rgba(0, 122, 255, 0.05)', border: '1px dashed rgba(0, 122, 255, 0.3)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)', fontWeight: 700, fontSize: 14 }}>
                  מבצע קבוע (ללא הגבלת זמן)
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div style={{ background: 'rgba(0,0,0,0.02)', border: '1px dashed var(--border)', borderRadius: 16, padding: '16px', fontSize: 13, color: 'var(--text-muted)', margin: '24px 0', lineHeight: 1.6, textAlign: 'center' }}>
        <b style={{ color: 'var(--text-main)' }}>שים לב:</b> כל משתמש שיצטרף בטווח התאריכים שהוגדר יקבל את ההטבה בצורה אוטומטית בעת רישומו. תוקף ההטבה של המשתמש נספר מיום ההצטרפות <b>שלו</b>. ביום האחרון של חבילת ההטבה שלו, המערכת תשלח לו התראה אוטומטית.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: (settings.promo_searches ?? 0) !== 0 ? '1fr 1fr' : '1fr', gap: 16 }}>
        <button className="btn" style={{ height: 50, borderRadius: 12, fontSize: 16, fontWeight: 800, background: '#047857', color: '#fff', border: 'none', boxShadow: '0 4px 12px rgba(16, 185, 129, 0.2)', cursor: saving ? 'default' : 'pointer', opacity: saving ? 0.7 : 1 }} disabled={saving} onClick={savePromo}>
          {saving ? '⏳ שומר נתונים...' : '✨ שמור והפעל מבצע הצטרפות'}
        </button>
        {(settings.promo_searches ?? 0) !== 0 && (
          <button className="btn" style={{ height: 50, borderRadius: 12, fontSize: 16, fontWeight: 800, background: '#c53030', color: '#fff', border: 'none', boxShadow: '0 4px 12px rgba(239, 68, 68, 0.2)', cursor: saving ? 'default' : 'pointer', opacity: saving ? 0.7 : 1 }} disabled={saving} onClick={clearPromo}>
            🗑️ ביטול מבצע פעיל
          </button>
        )}
      </div>
    </div>
  )
}

function FeaturesTab() {
  const [settings, setSettings]                 = useState(null)
  const [yad2Enabled, setYad2Enabled]           = useState(false)
  const [yad2Public, setYad2Public]             = useState(false)
  const [yad2PublicStart, setYad2PublicStart]   = useState('')
  const [yad2PublicEnd, setYad2PublicEnd]       = useState('')
  const [yad2PublicLabel, setYad2PublicLabel]   = useState('')
  const [yad2Saving, setYad2Saving]             = useState(false)
  const [pdfEnabled, setPdfEnabled]             = useState(false)
  const [pdfPublic, setPdfPublic]               = useState(false)
  const [pdfPublicStart, setPdfPublicStart]     = useState('')
  const [pdfPublicEnd, setPdfPublicEnd]         = useState('')
  const [pdfPublicLabel, setPdfPublicLabel]     = useState('')
  const [pdfSaving, setPdfSaving]               = useState(false)
  const [watchEnabled, setWatchEnabled]         = useState(false)
  const [watchMax, setWatchMax]                 = useState('2')
  const [watchPublic, setWatchPublic]           = useState(false)
  const [watchPublicStart, setWatchPublicStart] = useState('')
  const [watchPublicEnd, setWatchPublicEnd]     = useState('')
  const [watchPublicLabel, setWatchPublicLabel] = useState('')
  const [watchSaving, setWatchSaving]           = useState(false)

  useEffect(() => {
    adminFetchSettings().then(s => {
      setSettings(s)
      setYad2Enabled(!!s.yad2_market_enabled)
      setYad2Public(!!s.yad2_market_public)
      setYad2PublicStart(s.yad2_market_public_start || '')
      setYad2PublicEnd(s.yad2_market_public_end || '')
      setYad2PublicLabel(s.yad2_market_public_label || '')
      setPdfEnabled(!!s.pdf_report_enabled)
      setPdfPublic(!!s.pdf_report_public)
      setPdfPublicStart(s.pdf_report_public_start || '')
      setPdfPublicEnd(s.pdf_report_public_end || '')
      setPdfPublicLabel(s.pdf_report_public_label || '')
      setWatchEnabled(!!s.yad2_watch_enabled)
      setWatchMax(String(s.yad2_watch_max ?? 2))
      setWatchPublic(!!s.yad2_watch_public)
      setWatchPublicStart(s.yad2_watch_public_start || '')
      setWatchPublicEnd(s.yad2_watch_public_end || '')
      setWatchPublicLabel(s.yad2_watch_public_label || '')
    }).catch(() => {})
  }, [])

  async function saveYad2() {
    setYad2Saving(true)
    try {
      await adminUpdateSettings({
        yad2_market_enabled:      yad2Enabled,
        yad2_market_public:        yad2Public,
        yad2_market_public_start:  yad2PublicStart,
        yad2_market_public_end:    yad2PublicEnd,
        yad2_market_public_label:  yad2PublicLabel,
      })
      window.Telegram?.WebApp?.showAlert('✅ הגדרות עודכנו')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setYad2Saving(false)
  }

  async function savePdf() {
    setPdfSaving(true)
    try {
      await adminUpdateSettings({
        pdf_report_enabled:      pdfEnabled,
        pdf_report_public:       pdfPublic,
        pdf_report_public_start: pdfPublicStart,
        pdf_report_public_end:   pdfPublicEnd,
        pdf_report_public_label: pdfPublicLabel,
      })
      window.Telegram?.WebApp?.showAlert('✅ הגדרות עודכנו')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setPdfSaving(false)
  }

  if (!settings) return <div className="loading"></div>

  return (
    <div className="tab-fade-in">
      <div className="card" style={{ padding: '20px', marginBottom: 24, background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.05), transparent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <span style={{ fontSize: 24 }}>⭐</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>פיצ'רים מתקדמים למנויים</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>הגדרות גישה לפיצ'רים ייחודיים שפתוחים למנויים פעילים</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 20 }}>
        {/* Yad2 market price */}
        <div className="card" style={{ padding: '24px', borderTop: '4px solid #9a4a07' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 24, background: 'rgba(245, 158, 11, 0.1)', width: 44, height: 44, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>💰</span>
              <div>
                <div style={{ fontWeight: 800, fontSize: 16, color: 'var(--text-main)' }}>שווי שוק Yad2</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>הצגת נתוני שווי שוק על בסיס לוח יד2</div>
              </div>
            </div>
            <label className="toggle-row" style={{ margin: 0, padding: 0 }}>
              <button type="button" role="switch" aria-checked={!!yad2Enabled} aria-label="מחיר שוק Yad2 — הפעלה" className={`toggle ${yad2Enabled ? 'on' : ''}`} onClick={() => setYad2Enabled(v => !v)} style={{ margin: 0 }} />
            </label>
          </div>

          {yad2Enabled && (
            <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 16, animation: 'fadeIn 0.3s' }}>
              <div style={{ background: 'var(--bg)', borderRadius: 16, padding: '20px', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: yad2Public ? 16 : 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 18 }}>🌐</span>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>פתוח לכולם (חינמי)</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>הפעלת הפיצ'ר גם למשתמשים ללא מנוי</div>
                    </div>
                  </div>
                  <button type="button" role="switch" aria-checked={!!yad2Public} aria-label="מחיר שוק Yad2 — פתוח גם ללא מנוי" className={`toggle ${yad2Public ? 'on' : ''}`} onClick={() => setYad2Public(v => !v)} />
                </div>
                
                {yad2Public && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>טקסט תצוגה למשתמש</div>
                      <input type="text" className="input" style={{ margin: 0, borderRadius: 10 }}
                        placeholder='לדוגמה: פתוח לכולם עד 01/07/2026'
                        value={yad2PublicLabel} onChange={e => setYad2PublicLabel(e.target.value)} />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>תאריך התחלה</div>
                        <input type="date" aria-label="תאריך התחלה" className="input" style={{ margin: 0, borderRadius: 10 }}
                          value={yad2PublicStart} onChange={e => setYad2PublicStart(e.target.value)} />
                      </div>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>תאריך סיום</div>
                        <input type="date" aria-label="תאריך סיום" className="input" style={{ margin: 0, borderRadius: 10 }}
                          value={yad2PublicEnd} onChange={e => setYad2PublicEnd(e.target.value)} />
                      </div>
                    </div>
                    {(() => {
                      const today = new Date().toISOString().slice(0, 10)
                      const inWindow = (!yad2PublicStart || today >= yad2PublicStart) &&
                                       (!yad2PublicEnd   || today <= yad2PublicEnd)
                      return (
                        <div style={{ fontSize: 12, fontWeight: 700, color: inWindow ? '#047857' : '#9a4a07', background: inWindow ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)', padding: '8px 12px', borderRadius: 8, display: 'inline-block', marginTop: 4 }}>
                          {inWindow ? '🟢 פעיל כעת לכולם' : '🟡 מחוץ לטווח התאריכים (מוסתר מחינמיים)'}
                        </div>
                      )
                    })()}
                  </div>
                )}
              </div>
            </div>
          )}

          <button className="btn" style={{ marginTop: 20, width: '100%', height: 44, borderRadius: 12, fontWeight: 700, background: 'var(--bg)', border: '1px solid var(--primary)', color: 'var(--primary)' }} disabled={yad2Saving} onClick={saveYad2}>
            {yad2Saving ? '⏳ שומר...' : '💾 שמור הגדרות שווי שוק'}
          </button>
        </div>

        {/* PDF report */}
        <div className="card" style={{ padding: '24px', borderTop: '4px solid #c53030' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 24, background: 'rgba(239, 68, 68, 0.1)', width: 44, height: 44, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>📄</span>
              <div>
                <div style={{ fontWeight: 800, fontSize: 16, color: 'var(--text-main)' }}>הורדת דוח PDF</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>הפקת קובץ דוח מלא ושמירתו</div>
              </div>
            </div>
            <label className="toggle-row" style={{ margin: 0, padding: 0 }}>
              <button type="button" role="switch" aria-checked={!!pdfEnabled} aria-label="דוח PDF — הפעלה" className={`toggle ${pdfEnabled ? 'on' : ''}`} onClick={() => setPdfEnabled(v => !v)} style={{ margin: 0 }} />
            </label>
          </div>

          {pdfEnabled && (
            <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 16, animation: 'fadeIn 0.3s' }}>
              <div style={{ background: 'var(--bg)', borderRadius: 16, padding: '20px', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: pdfPublic ? 16 : 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 18 }}>🌐</span>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>פתוח לכולם (חינמי)</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>הפעלת הפיצ'ר גם למשתמשים ללא מנוי</div>
                    </div>
                  </div>
                  <button type="button" role="switch" aria-checked={!!pdfPublic} aria-label="דוח PDF — פתוח גם ללא מנוי" className={`toggle ${pdfPublic ? 'on' : ''}`} onClick={() => setPdfPublic(v => !v)} />
                </div>
                
                {pdfPublic && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>טקסט תצוגה למשתמש</div>
                      <input type="text" className="input" style={{ margin: 0, borderRadius: 10 }}
                        placeholder='לדוגמה: פתוח לכולם עד 01/07/2026'
                        value={pdfPublicLabel} onChange={e => setPdfPublicLabel(e.target.value)} />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>תאריך התחלה</div>
                        <input type="date" aria-label="תאריך התחלה" className="input" style={{ margin: 0, borderRadius: 10 }}
                          value={pdfPublicStart} onChange={e => setPdfPublicStart(e.target.value)} />
                      </div>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>תאריך סיום</div>
                        <input type="date" aria-label="תאריך סיום" className="input" style={{ margin: 0, borderRadius: 10 }}
                          value={pdfPublicEnd} onChange={e => setPdfPublicEnd(e.target.value)} />
                      </div>
                    </div>
                    {(() => {
                      const today = new Date().toISOString().slice(0, 10)
                      const inWindow = (!pdfPublicStart || today >= pdfPublicStart) &&
                                       (!pdfPublicEnd   || today <= pdfPublicEnd)
                      return (
                        <div style={{ fontSize: 12, fontWeight: 700, color: inWindow ? '#047857' : '#9a4a07', background: inWindow ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)', padding: '8px 12px', borderRadius: 8, display: 'inline-block', marginTop: 4 }}>
                          {inWindow ? '🟢 פעיל כעת לכולם' : '🟡 מחוץ לטווח התאריכים (מוסתר מחינמיים)'}
                        </div>
                      )
                    })()}
                  </div>
                )}
              </div>
            </div>
          )}

          <button className="btn" style={{ marginTop: 20, width: '100%', height: 44, borderRadius: 12, fontWeight: 700, background: 'var(--bg)', border: '1px solid var(--primary)', color: 'var(--primary)' }} disabled={pdfSaving} onClick={savePdf}>
            {pdfSaving ? '⏳ שומר...' : '💾 שמור הגדרות דוח PDF'}
          </button>
        </div>

        {/* Yad2 Watch alerts */}
        <div className="card" style={{ padding: '24px', borderTop: '4px solid #0066d6' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 24, background: 'rgba(59, 130, 246, 0.1)', width: 44, height: 44, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>🔔</span>
              <div>
                <div style={{ fontWeight: 800, fontSize: 16, color: 'var(--text-main)' }}>התראות יד2 בזמן אמת</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>מעקב התראות על רכבים חדשים ביד2</div>
              </div>
            </div>
            <label className="toggle-row" style={{ margin: 0, padding: 0 }}>
              <button type="button" role="switch" aria-checked={!!watchEnabled} aria-label="התראות יד2 — הפעלה" className={`toggle ${watchEnabled ? 'on' : ''}`} onClick={() => setWatchEnabled(v => !v)} style={{ margin: 0 }} />
            </label>
          </div>

          {watchEnabled && (
            <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 16, animation: 'fadeIn 0.3s' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg)', padding: '16px', borderRadius: 12, border: '1px solid var(--border)' }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>מגבלת התראות פעילות למשתמש</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>כמות החיפושים שמשתמש יכול לעקוב אחריהם</div>
                </div>
                <input type="number" min="1" max="20" className="input"
                  style={{ width: 80, margin: 0, textAlign: 'center', borderRadius: 10, fontSize: 16, fontWeight: 700 }}
                  value={watchMax} onChange={e => setWatchMax(e.target.value)} />
              </div>
              
              <div style={{ background: 'var(--bg)', borderRadius: 16, padding: '20px', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: watchPublic ? 16 : 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 18 }}>🌐</span>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-main)' }}>פתוח לכולם (חינמי)</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>הפעלת הפיצ'ר גם למשתמשים ללא מנוי</div>
                    </div>
                  </div>
                  <button type="button" role="switch" aria-checked={!!watchPublic} aria-label="התראות יד2 — פתוח גם ללא מנוי" className={`toggle ${watchPublic ? 'on' : ''}`} onClick={() => setWatchPublic(v => !v)} />
                </div>
                
                {watchPublic && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>טקסט תצוגה למשתמש</div>
                      <input type="text" className="input" style={{ margin: 0, borderRadius: 10 }}
                        placeholder='לדוגמה: פתוח לכולם עד 01/07/2026'
                        value={watchPublicLabel} onChange={e => setWatchPublicLabel(e.target.value)} />
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>תאריך התחלה</div>
                        <input type="date" aria-label="תאריך התחלה" className="input" style={{ margin: 0, borderRadius: 10 }}
                          value={watchPublicStart} onChange={e => setWatchPublicStart(e.target.value)} />
                      </div>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>תאריך סיום</div>
                        <input type="date" aria-label="תאריך סיום" className="input" style={{ margin: 0, borderRadius: 10 }}
                          value={watchPublicEnd} onChange={e => setWatchPublicEnd(e.target.value)} />
                      </div>
                    </div>
                    {(() => {
                      const today = new Date().toISOString().slice(0, 10)
                      const inWindow = (!watchPublicStart || today >= watchPublicStart) &&
                                       (!watchPublicEnd   || today <= watchPublicEnd)
                      return (
                        <div style={{ fontSize: 12, fontWeight: 700, color: inWindow ? '#047857' : '#9a4a07', background: inWindow ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)', padding: '8px 12px', borderRadius: 8, display: 'inline-block', marginTop: 4 }}>
                          {inWindow ? '🟢 פעיל כעת לכולם' : '🟡 מחוץ לטווח התאריכים (מוסתר מחינמיים)'}
                        </div>
                      )
                    })()}
                  </div>
                )}
              </div>
            </div>
          )}

          <button className="btn" style={{ marginTop: 20, width: '100%', height: 44, borderRadius: 12, fontWeight: 700, background: 'var(--bg)', border: '1px solid var(--primary)', color: 'var(--primary)' }} disabled={watchSaving} onClick={async () => {
            setWatchSaving(true)
            try {
              await adminUpdateSettings({
                yad2_watch_enabled:       watchEnabled,
                yad2_watch_max:           parseInt(watchMax) || 2,
                yad2_watch_public:        watchPublic,
                yad2_watch_public_start:  watchPublicStart,
                yad2_watch_public_end:    watchPublicEnd,
                yad2_watch_public_label:  watchPublicLabel,
              })
              window.Telegram?.WebApp?.showAlert('✅ הגדרות עודכנו')
            } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
            setWatchSaving(false)
          }}>
            {watchSaving ? '⏳ שומר...' : '💾 שמור הגדרות התראות'}
          </button>
        </div>
      </div>
    </div>
  )
}

function SettingsTab() {
  const [settings, setSettings]     = useState(null)
  const [saving, setSaving]         = useState(false)
  const [savingKey, setSavingKey]   = useState(null)   // which toggle card is being saved
  const [loadError, setLoadError]   = useState(false)
  const [toggleError, setToggleError] = useState('')
  const [freeInput, setFreeInput]   = useState('')
  const [referralInput, setReferralInput] = useState('')
  const [referralDaysInput, setReferralDaysInput] = useState('')

  function loadSettings() {
    setLoadError(false)
    adminFetchSettings().then(s => {
      setSettings(s)
      setFreeInput(String(s.free_searches ?? 10))
      setReferralInput(String(s.referral_bonus ?? 10))
      setReferralDaysInput(String(s.referral_bonus_premium_days ?? 0))
    }).catch(() => setLoadError(true))
  }

  useEffect(() => { loadSettings() }, [])

  async function toggleMaintenance() {
    setSaving(true)
    try {
      await adminUpdateSettings({ maintenance: !settings.maintenance })
      setSettings(s => ({ ...s, maintenance: !s.maintenance }))
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function toggleSetting(key) {
    setSavingKey(key)
    setToggleError('')
    try {
      await adminUpdateSettings({ [key]: !settings[key] })
      setSettings(s => ({ ...s, [key]: !s[key] }))
    } catch { setToggleError('השמירה נכשלה, נסה שוב') }
    setSavingKey(null)
  }

  async function saveFree() {
    setSaving(true)
    try {
      const v = parseInt(freeInput) || 0
      await adminUpdateSettings({ free_searches: v })
      setSettings(s => ({ ...s, free_searches: v }))
      window.Telegram?.WebApp?.showAlert('✅ עודכן בהצלחה')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function saveReferral() {
    setSaving(true)
    try {
      const days = Math.max(0, parseInt(referralDaysInput) || 0)
      await adminUpdateSettings({ referral_bonus: parseInt(referralInput), referral_bonus_premium_days: days })
      setSettings(s => ({ ...s, referral_bonus: parseInt(referralInput), referral_bonus_premium_days: days }))
      window.Telegram?.WebApp?.showAlert('✅ עודכן בהצלחה')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  if (loadError) return (
    <div className="card" style={{ padding: 20, textAlign: 'center' }}>
      <div style={{ marginBottom: 12 }}>טעינת ההגדרות נכשלה</div>
      <button className="btn btn-primary" onClick={loadSettings}>נסה שוב</button>
    </div>
  )
  if (!settings) return <div className="loading"></div>

  return (
    <div className="tab-fade-in">
      <div className="card" style={{ padding: '20px', marginBottom: 24, background: 'linear-gradient(135deg, rgba(75, 85, 99, 0.05), transparent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 24 }}>⚙️</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>הגדרות מערכת</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>ניהול תצורת בוט ומדיניות חיפושים</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {/* Maintenance */}
        <div className="card" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderLeft: settings.maintenance ? '4px solid #c53030' : '4px solid #047857' }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              🔧 מצב תחזוקה
              <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 10, background: settings.maintenance ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)', color: settings.maintenance ? '#c53030' : '#047857', fontWeight: 700 }}>
                {settings.maintenance ? 'פעיל' : 'כבוי'}
              </span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>משבית זמנית את הגישה לבוט עבור משתמשים רגילים</div>
          </div>
          <button
            type="button" role="switch" aria-checked={!!settings.maintenance} aria-label="מצב תחזוקה"
            className={`toggle ${settings.maintenance ? 'on' : ''}`}
            onClick={toggleMaintenance}
            disabled={saving}
            style={{ margin: 0, opacity: saving ? 0.6 : 1 }}
          />
        </div>

        {/* Bot feature toggles */}
        {toggleError && <div role="alert" style={{ color: 'var(--danger)', fontSize: 13, fontWeight: 700 }}>{toggleError}</div>}
        {[
          { key: 'rich_messages_enabled', icon: '📊', title: 'תוצאת חיפוש כטבלה', desc: 'כרטיס התוצאה, ההשוואה וההיסטוריה בבוט נשלחים כטבלה. אם השליחה נכשלת, נשלח כרטיס רגיל.' },
          { key: 'test_reminders_enabled', icon: '🔔', title: 'תזכורות טסט', desc: 'הבוט מזכיר חודש, שבוע ויום לפני פקיעת הטסט, למי שביקש תזכורת.' },
          { key: 'mirror_enabled', icon: '🪞', title: 'מראה פעולות לקבוצה', desc: 'כל פעולה של משתמש בבוט, והתשובה שקיבל, מועתקות לטופיק בקבוצה שלך בדיוק כפי שהמשתמש ראה אותן: אותו עיצוב, תמונות וטבלאות, וכפתורים שאינם פעילים. קודי הטבה ותוכן מוצרים דיגיטליים מוסתרים.', needsBind: !settings.mirror_bound },
          { key: 'mirror_miniapp', icon: '📱', title: 'מראה: פעולות במיני-אפ', desc: 'מוסיף למראה שורה על כל פעולה במיני-אפ (חיפוש, רכישה, מוסך, מעקב, פנייה). פועל רק כשמראה הפעולות פעילה.' },
          { key: 'test_reminders_garage_sync', icon: '🚗', title: 'תזכורת אוטומטית לרכבי המוסך', desc: 'מצרף לתזכורות גם כל רכב שמשתמש שמר ב"רכבים שקניתי", בלי שביקש. פועל רק כשתזכורות טסט פעילות.' },
        ].map(f => {
          const on = !!settings[f.key]
          return (
            <div key={f.key} className="card" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, borderLeft: on ? '4px solid #047857' : '4px solid #9ca3af', opacity: savingKey === f.key ? 0.6 : 1 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)', display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 4 }}>
                  <span>{f.icon} {f.title}</span>
                  <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 10, background: on ? 'rgba(4, 120, 87, 0.1)' : 'rgba(156, 163, 175, 0.15)', color: on ? '#047857' : '#4b5563', fontWeight: 700 }}>
                    {on ? 'פעיל' : 'כבוי'}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{f.desc}</div>
                {f.needsBind && <div style={{ fontSize: 13, color: 'var(--danger)', fontWeight: 700, marginTop: 6 }}>⚠️ עדיין לא מקושר לטופיק. שלח לבוט <span dir="ltr">/mirror_set &lt;topic link&gt;</span>, או <span dir="ltr">/mirror_here</span> בתוך הטופיק.</div>}
              </div>
              <button
                type="button" role="switch" aria-checked={on} aria-label={f.title}
                className={`toggle ${on ? 'on' : ''}`}
                onClick={() => toggleSetting(f.key)}
                disabled={savingKey !== null}
                style={{ margin: 0 }}
              />
            </div>
          )
        })}

        {/* Free searches */}
        <div className="card" style={{ padding: '20px', borderLeft: '4px solid #0066d6' }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
            🆓 חיפושים חינמיים ללקוח חדש
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>כמות החיפושים החינמיים שיקבל כל משתמש חדש שנרשם לבוט.</div>
          
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <div style={{ position: 'absolute', top: 0, bottom: 0, right: 14, display: 'flex', alignItems: 'center', color: 'var(--text-muted)' }}>🔍</div>
              <input 
                className="input" 
                type="number" 
                min="0" 
                aria-label="חיפושים חינם למשתמש חדש"
                value={freeInput} 
                onChange={e => setFreeInput(e.target.value)} 
                style={{ margin: 0, paddingRight: 40, height: 48, borderRadius: 12, fontWeight: 700, fontSize: 16 }}
              />
            </div>
            <button 
              className="btn" 
              disabled={saving} 
              onClick={saveFree}
              style={{ margin: 0, width: 'auto', padding: '0 24px', height: 48, borderRadius: 12, fontWeight: 700 }}
            >
              {saving ? '⏳...' : 'שמור שינויים'}
            </button>
          </div>
        </div>

        {/* Referral bonus */}
        <div className="card" style={{ padding: '20px', borderLeft: '4px solid #0066d6' }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
            🤝 בונוס הפניית חברים
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>הטבה למשתמש שהפנה חבר, לפי סוג המנוי שלו: משתמש חינמי / חבילת חיפושים מקבל חיפושים, ומנוי Premium (מסלול ללא הגבלה) מקבל ימים נוספים במסלול.</div>
          
          <label htmlFor="ref-days" style={{ display: 'block', fontSize: 13, fontWeight: 700, marginBottom: 6 }}>מנוי Premium — ימים נוספים במסלול לכל הפניה (0 = ללא הטבה)</label>
          <input
            id="ref-days"
            className="input"
            type="number"
            min="0"
            max="365"
            value={referralDaysInput}
            onChange={e => setReferralDaysInput(e.target.value)}
            style={{ marginTop: 0, marginBottom: 14, height: 48, borderRadius: 12, fontWeight: 700, fontSize: 16 }}
          />
          <label htmlFor="ref-searches" style={{ display: 'block', fontSize: 13, fontWeight: 700, marginBottom: 6 }}>משתמש חינמי — חיפושים לכל הפניה</label>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ position: 'relative', flex: 1 }}>
              <div style={{ position: 'absolute', top: 0, bottom: 0, right: 14, display: 'flex', alignItems: 'center', color: 'var(--text-muted)' }}>🎁</div>
              <input 
                id="ref-searches"
                className="input" 
                type="number" 
                min="1" 
                value={referralInput} 
                onChange={e => setReferralInput(e.target.value)} 
                style={{ margin: 0, paddingRight: 40, height: 48, borderRadius: 12, fontWeight: 700, fontSize: 16 }}
              />
            </div>
            <button 
              className="btn" 
              disabled={saving} 
              onClick={saveReferral}
              style={{ margin: 0, width: 'auto', padding: '0 24px', height: 48, borderRadius: 12, fontWeight: 700 }}
            >
              {saving ? '⏳...' : 'שמור שינויים'}
            </button>
          </div>
        </div>

        <MaintenanceTools />
      </div>
    </div>
  )
}

// One-off, irreversible admin operations (test-data cleanup). Each needs an explicit second tap.
function MaintenanceTools() {
  const [pending, setPending] = useState(null)   // 'purchases' | 'premium' | null
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState('')

  const ACTIONS = {
    purchases: {
      title: 'איפוס היסטוריית רכישות ותשלומים',
      warn: 'כל ההזמנות, התשלומים הממתינים והיסטוריית הרכישות יימחקו לצמיתות ומונה ההזמנות יתאפס. לא יישלחו הודעות למשתמשים.',
      button: 'כן, אפס רכישות ותשלומים',
      run: () => adminMaintenance('reset-purchases', 'RESET'),
      done: r => `נמחקו ${r.deleted?.paypal_transactions ?? 0} הזמנות ו-${r.deleted?.pending_payments ?? 0} תשלומים ממתינים.`,
    },
    premium: {
      title: 'מסלול Premium לכל המשתמשים',
      warn: 'כל המשתמשים (חוץ ממך ומשתמשים חסומים) יועברו למסלול Premium ל-30 יום מהיום, וייכנסו לקבוצת המנויים. לא יישלחו הודעות למשתמשים.',
      button: 'כן, העבר את כולם ל-Premium',
      run: () => adminMaintenance('grant-premium-all', 'GRANT'),
      done: r => `${r.users ?? 0} משתמשים עברו ל-Premium עד ${(r.expires || '').slice(0, 10)}.`,
    },
  }

  async function run() {
    const a = ACTIONS[pending]
    setBusy(true); setResult('')
    try {
      setResult(a.done(await a.run()))
      setPending(null)
    } catch { setResult('הפעולה נכשלה. לא בוצע שינוי מלא — נסה שוב או בדוק את הנתונים.') }
    setBusy(false)
  }

  return (
    <section className="card" style={{ padding: 20, borderLeft: '4px solid #d32f2f' }} aria-labelledby="maint-title">
      <h2 id="maint-title" style={{ fontSize: 15, fontWeight: 800, margin: '0 0 4px' }}>🧹 כלי תחזוקה (בלתי הפיכים)</h2>
      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
        פעולות חד-פעמיות לניקוי נתוני בדיקה. כל פעולה דורשת אישור נוסף ולא שולחת הודעות למשתמשים.
      </div>
      {!pending ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {Object.entries(ACTIONS).map(([k, a]) => (
            <button key={k} className="btn btn-outline" style={{ margin: 0, minHeight: 48 }} onClick={() => { setResult(''); setPending(k) }}>{a.title}</button>
          ))}
        </div>
      ) : (
        <div role="alertdialog" aria-labelledby="maint-confirm-title" style={{ border: '1.5px solid rgba(211,47,47,0.45)', borderRadius: 14, padding: 14 }}>
          <div id="maint-confirm-title" style={{ fontWeight: 800, marginBottom: 6 }}>⚠️ {ACTIONS[pending].title}</div>
          <div style={{ fontSize: 13, lineHeight: 1.7 }}>{ACTIONS[pending].warn}</div>
          <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
            <button className="btn btn-danger" style={{ flex: 1, margin: 0, minHeight: 48 }} disabled={busy} onClick={run}>{busy ? 'מבצע…' : ACTIONS[pending].button}</button>
            <button className="btn btn-outline" style={{ flex: 1, margin: 0, minHeight: 48 }} disabled={busy} onClick={() => setPending(null)}>ביטול</button>
          </div>
        </div>
      )}
      {result && <div role="status" style={{ marginTop: 10, fontSize: 13, fontWeight: 700 }}>{result}</div>}
    </section>
  )
}

function BroadcastTab() {
  const [msg, setMsg]             = useState('')
  const [imageb64, setImageb64]   = useState('')
  const [preview, setPreview]     = useState('')
  const [sending, setSending]     = useState(false)
  const [history, setHistory]     = useState(null)
  const [viewing, setViewing]     = useState(null)
  const [schedule, setSchedule]   = useState(false)
  const [when, setWhen]           = useState('')          // datetime-local value, device time
  const [scheduled, setScheduled] = useState(null)
  const fileRef                   = useRef()

  async function loadHistory() {
    try { setHistory(await adminFetchBroadcastHistory()) } catch { setHistory([]) }
    try { setScheduled(await adminFetchScheduledBroadcasts()) } catch { setScheduled([]) }
  }

  useEffect(() => { loadHistory() }, [])

  // earliest selectable time = now + 1 minute, in the datetime-local format
  function minWhen() {
    const d = new Date(Date.now() + 60_000)
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
    return d.toISOString().slice(0, 16)
  }

  const SCHEDULE_STATUS = { pending: '⏳ ממתין', sending: '📤 נשלח כעת', sent: '✅ נשלח', cancelled: '🚫 בוטל', missed: '⚠️ הוחמץ', interrupted: '⚠️ הופסק', failed: '❌ נכשל' }

  async function cancelScheduled(item) {
    window.Telegram?.WebApp?.showConfirm('לבטל את השידור המתוזמן?', async ok => {
      if (!ok) return
      try { await adminCancelScheduledBroadcast(item.id); await loadHistory() }
      catch { window.Telegram?.WebApp?.showAlert('לא ניתן לבטל — ייתכן שהשידור כבר נשלח') }
    })
  }

  function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const canvas = document.createElement('canvas')
    const img = new Image()
    img.onload = () => {
      const MAX = 1200
      let w = img.width, h = img.height
      if (w > MAX || h > MAX) {
        if (w > h) { h = Math.round(h * MAX / w); w = MAX }
        else        { w = Math.round(w * MAX / h); h = MAX }
      }
      canvas.width = w; canvas.height = h
      canvas.getContext('2d').drawImage(img, 0, 0, w, h)
      const b64 = canvas.toDataURL('image/jpeg', 0.82)
      setImageb64(b64)
      setPreview(b64)
    }
    img.src = URL.createObjectURL(file)
  }

  function clearImage() { setImageb64(''); setPreview(''); if (fileRef.current) fileRef.current.value = '' }

  async function send() {
    if (!msg.trim()) return
    let sendAt = null
    if (schedule) {
      const d = when ? new Date(when) : null
      if (!d || isNaN(d) || d.getTime() < Date.now() + 30_000) {
        window.Telegram?.WebApp?.showAlert('בחר תאריך ושעה עתידיים לשידור')
        return
      }
      sendAt = d.toISOString()
    }
    const question = sendAt
      ? `לתזמן את ההודעה ל-${fmtDateTime(sendAt)}?\n\n"${msg.slice(0, 80)}"`
      : `לשלוח הודעה לכל המשתמשים?\n\n"${msg.slice(0, 80)}"`
    window.Telegram?.WebApp?.showConfirm(
      question,
      async ok => {
        if (!ok) return
        setSending(true)
        try {
          const res = await adminBroadcast(msg.trim(), imageb64, sendAt)
          if (res.scheduled) {
            window.Telegram?.WebApp?.showAlert(`⏰ השידור תוזמן ל-${fmtDateTime(res.send_at)}`)
            setSchedule(false); setWhen('')
          } else {
            window.Telegram?.WebApp?.showAlert(`✅ נשלח ל-${res.sent} משתמשים${res.failed ? `, נכשל: ${res.failed}` : ''}`)
          }
          setMsg(''); clearImage()
          await loadHistory()
        } catch (e) { window.Telegram?.WebApp?.showAlert(e?.message && e.message !== 'Failed' ? e.message : 'שגיאה') }
        setSending(false)
      }
    )
  }

  function fmtDate(s) { return fmtDateTime(s) }

  return (
    <div className="tab-fade-in">
      <div className="card" style={{ padding: '20px', marginBottom: 24, background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.05), transparent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 24 }}>📢</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>שידור הודעות למשתמשים</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>שליחת הודעת Push / Broadcast לכל בסיס המנויים</div>
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: '20px', marginBottom: 24 }}>
        {/* Message input */}
        <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-main)', marginBottom: 12 }}>תוכן ההודעה</div>
        <textarea
          className="input"
          rows={5}
          placeholder="כתוב את ההודעה שתשלח לכלל המשתמשים בבוט (טקסט פשוט — כל משתמש יקבל אותה עם ברכה בשמו הפרטי)..."
          value={msg}
          onChange={e => setMsg(e.target.value)}
          style={{ resize: 'vertical', fontFamily: 'inherit', borderRadius: 12, marginBottom: 16, fontSize: 14 }}
        />

        {/* Image picker */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-main)', marginBottom: 12 }}>צירוף תמונה <span style={{ fontWeight: 500, color: 'var(--text-muted)', fontSize: 12 }}>(אופציונלי)</span></div>
          {preview ? (
            <div style={{ position: 'relative', display: 'inline-block' }}>
              <img src={preview} alt="" style={{ maxWidth: '100%', maxHeight: 200, borderRadius: 12, display: 'block', border: '1px solid var(--border)' }} />
              <button
                onClick={clearImage}
                style={{
                  position: 'absolute', top: 8, right: 8,
                  background: 'rgba(0,0,0,0.6)', color: '#fff',
                  border: 'none', borderRadius: '50%', width: 32, height: 32,
                  cursor: 'pointer', fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  backdropFilter: 'blur(4px)'
                }}
                title="הסר תמונה"
              >✕</button>
            </div>
          ) : (
            <div
              onClick={() => fileRef.current?.click()}
              style={{
                padding: '24px', borderRadius: 12, fontSize: 14, fontWeight: 600,
                border: '2px dashed var(--border)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                background: 'var(--bg)', color: 'var(--text-muted)', cursor: 'pointer', transition: 'all 0.2s'
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--primary)'; e.currentTarget.style.color = 'var(--primary)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-muted)' }}
            >
              <span style={{ fontSize: 24 }}>🖼️</span>
              לחץ כאן כדי להעלות תמונה
            </div>
          )}
          <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFile} />
        </div>

        {/* Scheduling */}
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: schedule ? 10 : 16, cursor: 'pointer', fontSize: 14, fontWeight: 800, color: 'var(--text-main)' }}>
          <input type="checkbox" checked={schedule} onChange={e => setSchedule(e.target.checked)} style={{ width: 20, height: 20 }} />
          ⏰ תזמן לשעה מאוחרת
        </label>
        {schedule && (
          <div style={{ marginBottom: 16 }}>
            <input
              type="datetime-local" className="input" value={when} min={minWhen()}
              onChange={e => setWhen(e.target.value)} aria-label="תאריך ושעה לשידור"
              style={{ width: '100%', borderRadius: 12, fontSize: 15, direction: 'ltr', textAlign: 'right' }}
            />
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>
              {when && !isNaN(new Date(when)) ? `יישלח ב-${fmtDateTime(new Date(when).toISOString())} (שעון ישראל)` : 'בחר תאריך ושעה. השידור נשלח אוטומטית, גם אם האפליקציה סגורה.'}
            </div>
          </div>
        )}

        <button className="btn" disabled={sending || !msg.trim() || (schedule && !when)} onClick={send} style={{ width: '100%', margin: 0, height: 50, borderRadius: 12, fontSize: 15, fontWeight: 800, background: 'var(--primary)', color: '#fff', boxShadow: '0 4px 12px rgba(0, 122, 255, 0.2)' }}>
          {sending ? (schedule ? '⏳ מתזמן...' : '⏳ מבצע שליחה המונית...') : (schedule ? '⏰ תזמן שידור' : '🚀 שלח הודעה לכולם עכשיו')}
        </button>
      </div>

      {/* Scheduled broadcasts */}
      {scheduled && scheduled.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)', marginBottom: 12 }}>⏰ שידורים מתוזמנים</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {scheduled.map(s => (
              <div key={s.id} className="card" style={{ padding: 14, borderRadius: 12, borderLeft: `4px solid ${s.status === 'pending' ? '#9a4a07' : s.status === 'sent' ? '#047857' : '#9ca3af'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 800 }}>{SCHEDULE_STATUS[s.status] || s.status}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{fmtDateTime(s.send_at)}</span>
                </div>
                <div style={{ fontSize: 14, color: 'var(--text-main)', lineHeight: 1.5, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                  {s.has_image ? '🖼️ ' : ''}{s.message}
                </div>
                {s.status === 'sent' && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 6 }}>נשלח ל-{s.sent}{s.failed ? `, נכשל: ${s.failed}` : ''}</div>}
                {s.status === 'pending' && (
                  <button className="btn" onClick={() => cancelScheduled(s)} style={{ margin: '10px 0 0', height: 36, padding: '0 14px', fontSize: 13, borderRadius: 10, background: 'transparent', color: 'var(--danger)', border: '1px solid var(--danger)' }}>
                    🚫 בטל תזמון
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* History */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-main)' }}>📋 היסטוריית שידורים</div>
        <button className="btn" onClick={loadHistory} style={{ margin: 0, padding: '4px 12px', height: 'auto', background: 'var(--bg-card)', border: '1px solid var(--border)', fontSize: 12, borderRadius: 8 }}>🔄 רענן</button>
      </div>
      
      {history === null && <div className="loading"></div>}
      {history && history.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40, background: 'var(--bg-card)', borderRadius: 16, border: '1px dashed var(--border)', color: 'var(--hint)', fontSize: 14 }}>
          טרם נשלחו הודעות שידור דרך המערכת
        </div>
      )}
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {history && history.map(h => (
          <div
            key={h.id}
            onClick={() => setViewing(h)}
            className="card"
            style={{
              padding: '16px', borderRadius: 12, cursor: 'pointer', transition: 'all 0.2s', borderLeft: '4px solid var(--primary)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 8 }}>
              <div style={{ fontSize: 14, fontWeight: 600, flex: 1, overflow: 'hidden', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', color: 'var(--text-main)', lineHeight: 1.5 }}>
                {h.has_image ? <span style={{ color: 'var(--primary)', marginLeft: 4 }}>🖼️</span> : null}
                {h.message}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap', fontWeight: 500, background: 'var(--bg)', padding: '4px 8px', borderRadius: 8 }}>
                {fmtDate(h.sent_at)}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 12, fontSize: 12, fontWeight: 600 }}>
              <span style={{ color: '#047857', display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#047857' }}></div>
                {h.sent} נשלחו
              </span>
              {h.failed > 0 && (
                <span style={{ color: '#c53030', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#c53030' }}></div>
                  {h.failed} נכשלו
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Viewer overlay */}
      {viewing && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, padding: 20
          }}
          onClick={() => setViewing(null)}
        >
          <div
            className="card tab-fade-in"
            style={{
              width: '100%', maxWidth: 480, maxHeight: '85vh',
              overflowY: 'auto', padding: 0, display: 'flex', flexDirection: 'column'
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ padding: '20px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-card)', position: 'sticky', top: 0, zIndex: 2 }}>
              <div style={{ fontWeight: 800, fontSize: 16, color: 'var(--text-main)' }}>פרטי ההודעה שנשלחה</div>
              <button onClick={() => setViewing(null)} style={{ background: 'var(--bg)', border: 'none', width: 32, height: 32, borderRadius: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--text-main)', fontSize: 14 }}>✕</button>
            </div>
            
            <div style={{ padding: '20px' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
                <div style={{ background: 'var(--bg)', padding: '6px 12px', borderRadius: 8, fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                  📅 נשלח ב: {fmtDate(viewing.sent_at)}
                </div>
                <div style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#047857', padding: '6px 12px', borderRadius: 8, fontSize: 12, fontWeight: 700 }}>
                  ✅ {viewing.sent} נשלחו בהצלחה
                </div>
                {viewing.failed > 0 && (
                  <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#c53030', padding: '6px 12px', borderRadius: 8, fontSize: 12, fontWeight: 700 }}>
                    ❌ {viewing.failed} נכשלו
                  </div>
                )}
                {viewing.has_image && (
                  <div style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#0066d6', padding: '6px 12px', borderRadius: 8, fontSize: 12, fontWeight: 700 }}>
                    🖼️ כולל תמונה
                  </div>
                )}
              </div>
              
              <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 700, marginBottom: 8 }}>תוכן ההודעה שנשלחה:</div>
              <div style={{
                background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px',
                fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'var(--text-main)'
              }}>
                {viewing.message}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const STATUS_LABEL = { open: 'פתוח', in_progress: 'בטיפול', closed: 'סגור' }
const STATUS_COLOR = { open: '#9a4a07', in_progress: '#0066d6', closed: '#047857' }
const STATUS_BG = { open: 'rgba(245, 158, 11, 0.1)', in_progress: 'rgba(59, 130, 246, 0.1)', closed: 'rgba(16, 185, 129, 0.1)' }

function TicketsTab() {
  const [allTickets, setAllTickets] = useState(null)
  const [filter, setFilter] = useState('open')
  const [selected, setSelected] = useState(null)

  async function load() {
    const data = await adminFetchTickets()
    setAllTickets(data)
  }

  useEffect(() => { load().catch(() => {}) }, [])

  if (selected) {
    return (
      <AdminTicketThread
        ticketId={selected}
        onBack={async () => { setSelected(null); await load() }}
      />
    )
  }

  const counts = allTickets ? {
    '': allTickets.length,
    open: allTickets.filter(t => t.status === 'open').length,
    in_progress: allTickets.filter(t => t.status === 'in_progress').length,
    closed: allTickets.filter(t => t.status === 'closed').length,
  } : {}

  const visible = allTickets ? (filter ? allTickets.filter(t => t.status === filter) : allTickets) : null

  return (
    <div className="tab-fade-in">
      <div className="card" style={{ padding: '20px', marginBottom: 24, background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.05), transparent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 24 }}>🎫</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>ניהול פניות שירות</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>מעקב וטיפול בפניות תמיכה של משתמשים</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {[['open', '🔴 פתוחות'], ['in_progress', '🟡 בטיפול'], ['closed', '🟢 סגורות'], ['', '📋 הכל']].map(([val, label]) => (
          <button
            key={val}
            onClick={() => setFilter(val)}
            style={{
              padding: '8px 16px', fontSize: 13, fontWeight: 700, borderRadius: 12, border: 'none',
              background: filter === val ? 'var(--primary)' : 'var(--bg-card)',
              color: filter === val ? '#fff' : 'var(--text-main)',
              cursor: 'pointer', transition: 'all 0.2s',
              boxShadow: filter === val ? '0 4px 12px rgba(0, 122, 255, 0.2)' : '0 2px 4px rgba(0,0,0,0.02)',
              border: filter === val ? '1px solid var(--primary)' : '1px solid var(--border)'
            }}
          >
            {label}{allTickets && counts[val] > 0 ? ` (${counts[val]})` : ''}
          </button>
        ))}
      </div>

      {!allTickets && <div className="loading"></div>}
      
      {visible && visible.length === 0 && (
        <div style={{ textAlign: 'center', padding: 40, background: 'var(--bg-card)', borderRadius: 16, border: '1px dashed var(--border)', color: 'var(--hint)', fontSize: 14 }}>
          אין פניות בקטגוריה זו
        </div>
      )}
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12 }}>
        {visible && visible.map(t => {
          const name = t.username ? `@${t.username}` : t.full_name || `id:${t.user_id}`
          return (
            <div key={t.id} className="card" style={{ padding: '16px', cursor: 'pointer', transition: 'all 0.2s', borderLeft: `4px solid ${STATUS_COLOR[t.status]}` }} onClick={() => setSelected(t.id)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)', marginBottom: 4 }}>
                    <span style={{ color: 'var(--text-muted)', fontSize: 13, marginRight: 6 }}>#{t.id}</span>
                    {t.subject}
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{name}</span>
                    <span>•</span>
                    <span>{fmtDateIL(t.created_at)}</span>
                  </div>
                </div>
                <span style={{
                  fontSize: 12, fontWeight: 700, padding: '4px 10px', borderRadius: 8,
                  background: STATUS_BG[t.status], color: STATUS_COLOR[t.status],
                  whiteSpace: 'nowrap', border: `1px solid ${STATUS_COLOR[t.status]}40`
                }}>
                  {STATUS_LABEL[t.status]}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function AdminTicketThread({ ticketId, onBack }) {
  const [ticket, setTicket] = useState(null)
  const [reply, setReply] = useState('')
  const [sending, setSending] = useState(false)
  const [updating, setUpdating] = useState(false)

  async function load() {
    const t = await adminFetchTicket(ticketId)
    setTicket(t)
  }

  useEffect(() => { load().catch(() => {}) }, [ticketId])

  async function sendReply() {
    if (!reply.trim()) return
    setSending(true)
    try {
      await adminReplyTicket(ticketId, reply.trim())
      setReply('')
      await load()
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSending(false)
  }

  async function changeStatus(status) {
    setUpdating(true)
    try {
      await adminUpdateTicketStatus(ticketId, status)
      await load()
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setUpdating(false)
  }

  if (!ticket) return <div className="loading"></div>

  const allMessages = [
    { id: 'orig', sender_name: ticket.full_name || ticket.username || `id:${ticket.user_id}`, is_admin: false, message: ticket.message, created_at: ticket.created_at },
    ...(ticket.replies || []),
  ]

  const name = ticket.username ? `@${ticket.username}` : ticket.full_name || `id:${ticket.user_id}`

  return (
    <div className="tab-fade-in" style={{ paddingBottom: 80, display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button onClick={onBack} style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', width: 36, height: 36, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--text-main)', fontSize: 16 }}>←</button>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 800, fontSize: 16, color: 'var(--text-main)' }}>פניה #{ticket.id}: {ticket.subject}</div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>מאת: <span style={{ fontWeight: 600 }}>{name}</span></div>
        </div>
      </div>

      <div className="card" style={{ padding: '12px', marginBottom: 20, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', background: 'var(--bg-card)' }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', marginLeft: 8 }}>סטטוס פניה:</span>
        {[['open','🔴 פתוח'], ['in_progress','🟡 בטיפול'], ['closed','🟢 סגור']].map(([val, label]) => (
          <button
            key={val}
            disabled={updating || ticket.status === val}
            onClick={() => changeStatus(val)}
            style={{
              padding: '6px 12px', fontSize: 13, fontWeight: 700, borderRadius: 8, border: 'none',
              background: ticket.status === val ? STATUS_BG[val] : 'var(--bg)',
              color: ticket.status === val ? STATUS_COLOR[val] : 'var(--text-muted)',
              border: `1px solid ${ticket.status === val ? STATUS_COLOR[val] + '40' : 'var(--border)'}`,
              cursor: ticket.status === val ? 'default' : 'pointer',
              opacity: updating ? 0.6 : 1, transition: 'all 0.2s'
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 20 }}>
        {allMessages.map((msg, i) => {
          const isAdmin = msg.is_admin
          return (
            <div key={msg.id || i} style={{
              display: 'flex', flexDirection: 'column',
              alignItems: isAdmin ? 'flex-end' : 'flex-start',
            }}>
              <div style={{
                maxWidth: '85%',
                background: isAdmin ? 'var(--primary)' : 'var(--bg-card)',
                color: isAdmin ? '#fff' : 'var(--text-main)',
                border: isAdmin ? 'none' : '1px solid var(--border)',
                borderRadius: isAdmin ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                padding: '12px 16px', fontSize: 14, lineHeight: 1.5, wordBreak: 'break-word',
                boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
              }}>
                {msg.message}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, fontWeight: 500, padding: '0 4px' }}>
                {isAdmin ? '🛠️ צוות תמיכה' : '👤 ' + name} • {fmtDateTime(msg.created_at)}
              </div>
            </div>
          )
        })}
      </div>

      {ticket.status !== 'closed' && (
        <div style={{ position: 'fixed', bottom: 0, right: 0, left: 0, padding: '16px', background: 'rgba(255,255,255,0.8)', backdropFilter: 'blur(12px)', borderTop: '1px solid var(--border)', zIndex: 10 }}>
          <div style={{ display: 'flex', gap: 12, maxWidth: 480, margin: '0 auto', background: 'var(--bg-card)', padding: '6px', borderRadius: 16, border: '1px solid var(--border)', boxShadow: '0 4px 16px rgba(0,0,0,0.06)' }}>
            <input
              style={{ flex: 1, margin: 0, border: 'none', background: 'transparent', padding: '0 12px', fontSize: 15, color: 'var(--text-main)', outline: 'none' }}
              placeholder="כתוב תגובה למשתמש..."
              value={reply}
              onChange={e => setReply(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendReply()}
            />
            <button
              style={{
                width: 44, height: 44, borderRadius: 12, border: 'none',
                background: reply.trim() ? 'var(--primary)' : 'var(--bg)',
                color: reply.trim() ? '#fff' : 'var(--text-muted)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18,
                cursor: reply.trim() && !sending ? 'pointer' : 'default', transition: 'all 0.2s',
                boxShadow: reply.trim() ? '0 4px 12px rgba(0, 122, 255, 0.2)' : 'none'
              }}
              disabled={sending || !reply.trim()}
              onClick={sendReply}
            >
              {sending ? '⏳' : '↑'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}


// ── Groups Tab ────────────────────────────────────────────────────────────────
function GroupsTab() {
  const [groups, setGroups] = useState(null)
  const [users, setUsers] = useState(null)
  const [newGroupName, setNewGroupName] = useState('')
  const [creating, setCreating] = useState(false)
  const [addingMember, setAddingMember] = useState({}) // groupId -> userId string
  const [confirmGroup, setConfirmGroup] = useState(null)
  const [deletingGroup, setDeletingGroup] = useState(false)

  async function loadGroups() {
    try { setGroups(await adminFetchGroups()) } catch { }
  }

  useEffect(() => {
    loadGroups()
    adminFetchUsers().then(setUsers).catch(() => {})
  }, [])

  async function createGroup() {
    const name = newGroupName.trim()
    if (!name) return
    setCreating(true)
    try {
      await adminCreateGroup(name)
      setNewGroupName('')
      await loadGroups()
    } catch (e) {
      window.Telegram?.WebApp?.showAlert('שגיאה: ' + (e.message || 'נסה שוב'))
    }
    setCreating(false)
  }

  async function deleteGroup(id) {
    // confirmation is the inline step on the card (confirmGroup)
    setDeletingGroup(true)
    try { await adminDeleteGroup(id); await loadGroups(); setConfirmGroup(null) }
    catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setDeletingGroup(false)
  }

  async function addMember(groupId) {
    const userId = parseInt(addingMember[groupId])
    if (!userId) return
    try {
      await adminAddGroupMember(groupId, userId)
      setAddingMember(m => ({ ...m, [groupId]: '' }))
      await loadGroups()
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
  }

  async function removeMember(groupId, userId) {
    try {
      await adminRemoveGroupMember(groupId, userId)
      await loadGroups()
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
  }

  function getUserName(uid) {
    if (!users) return String(uid)
    const u = users.find(u => u.user_id === uid)
    if (!u) return String(uid)
    return u.username ? `@${u.username}` : u.full_name || String(uid)
  }

  if (!groups) return <div className="loading"></div>

  // Users not already in the group
  function availableUsers(group) {
    if (!users) return []
    return users.filter(u => !group.member_ids.includes(u.user_id))
  }

  return (
    <div className="tab-fade-in">
      {/* Create group */}
      <div className="card" style={{ padding: '20px', marginBottom: 24, background: 'linear-gradient(to right, rgba(0, 122, 255, 0.05), transparent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <span style={{ fontSize: 24 }}>👥</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>קבוצות משתמשים</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>ניהול הרשאות וקבוצות תמחור</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <input
            className="input"
            style={{ flex: 1, marginBottom: 0, borderRadius: 12, height: 44 }}
            placeholder="שם הקבוצה החדשה..."
            value={newGroupName}
            onChange={e => setNewGroupName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && createGroup()}
          />
          <button
            className="btn"
            style={{ width: 'auto', padding: '0 24px', margin: 0, borderRadius: 12, background: 'var(--primary)', fontWeight: 700 }}
            disabled={creating || !newGroupName.trim()}
            onClick={createGroup}
          >
            {creating ? '⏳ יוצר...' : '➕ הוסף'}
          </button>
        </div>
      </div>

      {/* Groups list */}
      {groups.length === 0 && (
        <div style={{ color: 'var(--hint)', textAlign: 'center', padding: 32, background: 'var(--bg-card)', borderRadius: 16, border: '1px dashed var(--border)' }}>אין קבוצות מוגדרות למערכת</div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {groups.map(group => (
          <div key={group.id} className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, padding: '14px 16px', borderBottom: '1px solid var(--border)', background: 'rgba(0,0,0,0.02)' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 800, fontSize: 17, lineHeight: 1.3, color: 'var(--text-main)', overflowWrap: 'anywhere' }}>{group.name}</div>
                <div style={{ fontSize: 13, color: '#566070', marginTop: 2 }}>{group.member_ids.length} משתמשים משויכים</div>
              </div>
              <div style={{ flex: '0 0 72px' }}>
                <AdminItemBtn icon="🗑️" label="מחק" ariaLabel={`מחק קבוצה: ${group.name}`} danger onClick={() => setConfirmGroup(group.id)} />
              </div>
            </div>
            {confirmGroup === group.id && (
              <div style={{ padding: '0 16px 4px' }}>
                <AdminItemConfirm text={`למחוק את הקבוצה "${group.name}"? אי אפשר לבטל.`} busy={deletingGroup}
                  onYes={() => deleteGroup(group.id)} onNo={() => setConfirmGroup(null)} />
              </div>
            )}

            <div style={{ padding: '16px' }}>
              {/* Members */}
              {group.member_ids.length > 0 && (
                <div style={{ marginBottom: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {group.member_ids.map(uid => (
                    <div key={uid} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, minWidth: 0, padding: '6px 6px 6px 12px', background: 'var(--bg)', borderRadius: 12, border: '1px solid var(--border)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                        <div style={{ flex: '0 0 32px', width: 32, height: 32, borderRadius: '50%', background: 'rgba(0, 122, 255, 0.1)', color: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700 }}>
                          {uid.toString().slice(-2)}
                        </div>
                        <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-main)' }}>{getUserName(uid)}</span>
                      </div>
                      <button
                        onClick={() => removeMember(group.id, uid)}
                        aria-label={`הסר מהקבוצה: ${getUserName(uid)}`}
                        style={{ flex: '0 0 44px', background: 'rgba(239, 68, 68, 0.1)', border: 'none', color: '#b42318', cursor: 'pointer', width: 44, height: 44, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, transition: 'all 0.2s' }}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add member */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', background: 'var(--bg)', padding: '12px', borderRadius: 12, border: '1px dashed var(--border)' }}>
                <select
                  className="input"
                  aria-label={`הוספת משתמש לקבוצה ${group.name || ''}`}
                  style={{ flex: '1 1 100%', minWidth: 0, margin: 0, borderRadius: 10, height: 44, border: 'none', background: 'var(--bg-card)' }}
                  value={addingMember[group.id] || ''}
                  onChange={e => setAddingMember(m => ({ ...m, [group.id]: e.target.value }))}
                >
                  <option value="">בחר משתמש לצירוף...</option>
                  {availableUsers(group).map(u => (
                    <option key={u.user_id} value={u.user_id}>
                      {u.username ? `@${u.username}` : u.full_name || String(u.user_id)}
                    </option>
                  ))}
                </select>
                <button
                  className="btn btn-success"
                  style={{ flex: '1 1 100%', width: 'auto', padding: '0 16px', margin: 0, height: 44, borderRadius: 10, fontWeight: 700, background: '#047857' }}
                  disabled={!addingMember[group.id]}
                  onClick={() => addMember(group.id)}
                >
                  צרף לקבוצה
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function WatchesTab() {
  const [watches, setWatches] = useState(null)
  const [form, setForm] = useState({ make: '', model: '', year: '' })
  const [makes, setMakes] = useState([])
  const [models, setModels] = useState([])
  const [adding, setAdding] = useState(false)
  const [saving, setSaving] = useState(false)
  const [preview, setPreview] = useState(null)   // null | 'loading' | []
  const [previewWatch, setPreviewWatch] = useState(null)  // watch id being previewed

  function load() { adminFetchWatches().then(setWatches).catch(() => setWatches([])) }
  useEffect(() => { load() }, [])
  useEffect(() => {
    adminWatchMakes().then(setMakes).catch(() => {})
  }, [])
  useEffect(() => {
    if (!form.make) { setModels([]); setForm(f => ({ ...f, model: '' })); return }
    adminWatchModels(form.make).then(ms => { setModels(ms); setForm(f => ({ ...f, model: '' })) }).catch(() => setModels([]))
  }, [form.make])

  async function createWatch() {
    if (!form.make) return
    setSaving(true)
    try {
      await adminCreateWatch({
        make: form.make,
        model: form.model,
        year: form.year ? parseInt(form.year) : null,
      })
      setForm({ make: '', model: '', year: '' })
      setAdding(false)
      setPreview(null)
      load()
    } catch (e) { window.Telegram?.WebApp?.showAlert(e.message || 'שגיאה') }
    setSaving(false)
  }

  async function runPreview(make, model, year) {
    setPreview('loading')
    try {
      const data = await adminWatchPreview(make, model || '', year || null)
      // API now returns {items, total, search_url}
      setPreview(Array.isArray(data) ? { items: data, total: data.length, search_url: '' } : data)
    } catch (e) {
      setPreview({ items: [], total: 0, search_url: '' })
      window.Telegram?.WebApp?.showAlert('לא נמצאו מודעות / שגיאת חיבור')
    }
  }

  async function deleteWatch(id) {
    window.Telegram?.WebApp?.showConfirm('למחוק את ההתראה?', async ok => {
      if (!ok) return
      await adminDeleteWatch(id)
      if (previewWatch === id) { setPreview(null); setPreviewWatch(null) }
      load()
    })
  }

  async function toggleWatch(id) {
    await adminToggleWatch(id)
    load()
  }

  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: currentYear - 1999 }, (_, i) => currentYear - i)

  if (!watches) return <div className="loading"></div>

  return (
    <div className="tab-fade-in">
      <div className="card" style={{ padding: '20px', marginBottom: 24, background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.05), transparent)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 24 }}>🔔</span>
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--text-main)', letterSpacing: '-0.3px' }}>התראות יד2 למשתמשים</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>ניהול התראות מעקב אחר רכבים למשתמשים במערכת</div>
          </div>
        </div>
      </div>

      <div style={{ background: 'rgba(59, 130, 246, 0.05)', border: '1px solid rgba(59, 130, 246, 0.2)', borderRadius: 16, padding: '16px', fontSize: 13, color: 'var(--text-muted)', marginBottom: 24, lineHeight: 1.6 }}>
        <b style={{ color: 'var(--text-main)' }}>איך זה עובד:</b> הגדר מעקב אחר מודעות רכב. המערכת תבדוק אוטומטית כל 30 דקות אם פורסמו רכבים חדשים העונים לקריטריונים, ותשלח הודעת התראה בטלגרם. ניתן להגדיר עד 5 התראות במקביל.
      </div>

      {watches.length === 0 && !adding && (
        <div style={{ textAlign: 'center', padding: 40, background: 'var(--bg-card)', borderRadius: 16, border: '1px dashed var(--border)', color: 'var(--hint)', fontSize: 14 }}>
          אין התראות מוגדרות במערכת
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {watches.map(w => (
          <div key={w.id} className="card" style={{ padding: 0, overflow: 'hidden', opacity: w.active ? 1 : 0.6, transition: 'all 0.2s', borderLeft: w.active ? '4px solid #047857' : '4px solid #c53030' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px' }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 15, fontWeight: 800, color: 'var(--text-main)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                  {w.make}{w.model ? ` ${w.model}` : ''}{w.year ? ` - ${w.year}` : ''}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ color: w.active ? '#047857' : '#c53030', fontWeight: 600 }}>{w.active ? '🟢 פעיל עכשיו' : '🔴 מושהה'}</span>
                  <span>•</span>
                  <span>נוצר ב-{w.created_at?.slice(0, 10)}</span>
                </div>
              </div>
              
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  onClick={() => {
                    if (previewWatch === w.id) { setPreview(null); setPreviewWatch(null) }
                    else { setPreviewWatch(w.id); runPreview(w.make, w.model, w.year) }
                  }}
                  style={{
                    width: 36, height: 36, borderRadius: 10, background: 'var(--bg)', border: '1px solid var(--border)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', fontSize: 16, color: 'var(--text-main)'
                  }}
                  title="בדוק תוצאות"
                >🔍</button>
                <button
                  onClick={() => toggleWatch(w.id)}
                  style={{
                    width: 36, height: 36, borderRadius: 10, background: 'var(--bg)', border: '1px solid var(--border)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', fontSize: 16, color: 'var(--text-main)'
                  }}
                  title={w.active ? 'השהה' : 'הפעל'}
                >{w.active ? '⏸' : '▶️'}</button>
                <button
                  onClick={() => deleteWatch(w.id)}
                  style={{
                    width: 36, height: 36, borderRadius: 10, background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', fontSize: 16, color: '#c53030'
                  }}
                  title="מחק התראה"
                >🗑</button>
              </div>
            </div>

            {/* Preview panel */}
            {previewWatch === w.id && (
              <div style={{ padding: '16px', background: 'var(--bg)', borderTop: '1px solid var(--border)' }}>
                {preview === 'loading' && (
                  <div style={{ display: 'flex', justifyContent: 'center', padding: '20px' }}><div className="loading"></div></div>
                )}
                {preview?.items && preview.items.length === 0 && (
                  <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '12px' }}>לא נמצאו מודעות רלוונטיות</div>
                )}
                {preview?.items && preview.items.length > 0 && (
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 12 }}>
                      נמצאו {preview.total} מודעות (מציג עד 5 אחרונות):
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 8 }}>
                      {preview.items.map((item, i) => (
                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px', background: 'var(--bg-card)', borderRadius: 12, border: '1px solid var(--border)' }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontWeight: 800, fontSize: 14, color: '#0066d6', marginBottom: 4 }}>
                              {item.price ? `₪${Number(item.price).toLocaleString()}` : 'ללא מחיר'}
                            </div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', gap: 12 }}>
                              {item.km && <span>🛣️ {Number(item.km).toLocaleString()} ק"מ</span>}
                              {item.year && <span>📅 {item.year}</span>}
                              {item.city && <span>📍 {item.city}</span>}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                    {preview.search_url && (
                      <a href={preview.search_url} target="_blank" rel="noreferrer" style={{ display: 'block', textAlign: 'center', padding: '12px', background: 'rgba(59, 130, 246, 0.1)', color: '#0066d6', borderRadius: 12, fontSize: 14, fontWeight: 700, textDecoration: 'none', marginTop: 12, border: '1px solid rgba(59, 130, 246, 0.2)' }}>
                        פתח את כל התוצאות ביד2 ↗
                      </a>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {adding && (
          <div className="card tab-fade-in" style={{ padding: '24px', border: '2px solid var(--primary)', position: 'relative' }}>
            <div style={{ fontWeight: 800, fontSize: 16, color: 'var(--text-main)', marginBottom: 16 }}>הגדרת מעקב חדש</div>
            <button onClick={() => { setAdding(false); setForm({ make: '', model: '', year: '' }); setPreview(null) }} style={{ position: 'absolute', top: 20, right: 20, background: 'var(--bg)', border: 'none', width: 32, height: 32, borderRadius: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--text-main)', fontSize: 14 }}>✕</button>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6 }}>יצרן רכב</div>
                <select className="input" value={form.make} onChange={e => setForm(f => ({ ...f, make: e.target.value, model: '', year: '' }))} style={{ margin: 0, borderRadius: 12, background: 'var(--bg)', fontWeight: 600 }}>
                  <option value="">— בחר יצרן מרשימה —</option>
                  {makes.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>

              {form.make && (
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6 }}>דגם ספציפי (אופציונלי)</div>
                  <select className="input" value={form.model} onChange={e => setForm(f => ({ ...f, model: e.target.value }))} style={{ margin: 0, borderRadius: 12, background: 'var(--bg)', fontWeight: 600 }}>
                    <option value="">— כל הדגמים —</option>
                    {models.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              )}

              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 6 }}>שנתון (אופציונלי)</div>
                <select className="input" value={form.year} onChange={e => setForm(f => ({ ...f, year: e.target.value }))} style={{ margin: 0, borderRadius: 12, background: 'var(--bg)', fontWeight: 600 }}>
                  <option value="">— כל השנתונים —</option>
                  {years.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
              </div>

              {form.make && (
                <button
                  type="button"
                  style={{ padding: '12px', background: 'var(--bg)', border: '1px dashed var(--border)', borderRadius: 12, color: 'var(--text-main)', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}
                  onClick={() => runPreview(form.make, form.model, form.year ? parseInt(form.year) : null)}
                >
                  🔍 הפעל בדיקה מקדימה לפני שמירה
                </button>
              )}

              {/* Inline preview */}
              {preview === 'loading' && !previewWatch && (
                <div style={{ display: 'flex', justifyContent: 'center', padding: '10px' }}><div className="loading"></div></div>
              )}
              {preview?.items && !previewWatch && preview.items.length === 0 && (
                <div style={{ color: '#c53030', fontSize: 13, textAlign: 'center', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 12 }}>לא נמצאו מודעות תואמות, אולי כדאי להרחיב את החיפוש</div>
              )}
              {preview?.items && !previewWatch && preview.items.length > 0 && (
                <div style={{ background: 'var(--bg)', borderRadius: 12, padding: '16px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#047857', marginBottom: 12 }}>
                    נמצאו {preview.total} מודעות תואמות!
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {preview.items.slice(0,3).map((item, i) => (
                      <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px', background: 'var(--bg-card)', borderRadius: 8, border: '1px solid var(--border)' }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 800, fontSize: 13, color: '#0066d6', marginBottom: 2 }}>{item.price ? `₪${Number(item.price).toLocaleString()}` : 'ללא מחיר'}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                            {[item.km ? `${Number(item.km).toLocaleString()} ק"מ` : null, item.city].filter(Boolean).join(' • ')}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {preview.search_url && (
                    <a href={preview.search_url} target="_blank" rel="noreferrer" style={{ display: 'block', textAlign: 'center', padding: '10px', color: '#0066d6', fontSize: 13, fontWeight: 700, textDecoration: 'none', marginTop: 8 }}>
                      פתח את כל התוצאות ביד2 ↗
                    </a>
                  )}
                </div>
              )}

              <button
                className="btn"
                disabled={saving || !form.make}
                onClick={createWatch}
                style={{ height: 50, borderRadius: 12, fontSize: 16, fontWeight: 800, background: '#047857', color: '#fff', border: 'none', boxShadow: '0 4px 12px rgba(16, 185, 129, 0.2)', cursor: (saving || !form.make) ? 'default' : 'pointer', opacity: (saving || !form.make) ? 0.6 : 1, margin: 0, marginTop: 8 }}
              >
                {saving ? '⏳ שומר נתונים...' : '✨ הוסף מעקב חדש'}
              </button>
            </div>
          </div>
        )}

        {!adding && watches.length < 5 && (
          <button
            onClick={() => { setAdding(true); setPreview(null); setPreviewWatch(null) }}
            style={{ height: 50, borderRadius: 12, fontSize: 15, fontWeight: 800, background: 'var(--bg-card)', color: 'var(--primary)', border: '2px dashed var(--primary)', cursor: 'pointer', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
          >
            <span style={{ fontSize: 18 }}>➕</span>
            הגדר התראה חדשה למערכת
          </button>
        )}
      </div>
    </div>
  )
}

