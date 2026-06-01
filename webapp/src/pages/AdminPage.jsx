import { useState, useEffect, useRef } from 'react'
import { fmtDateTime, fmtDate as fmtDateIL, fmtTimeShort } from '../utils/time.js'
import { adminOrderApprove, adminOrderCancel } from '../api.js'
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
  adminBroadcast, adminFetchBroadcastHistory,
  adminToggleBlock,
  adminSendUserMessage,
  adminFetchUserHistory,
  adminFetchUserReferrals,
  adminFetchActivity,
  adminGiftAll,
  adminFetchGroups,
  adminCreateGroup,
  adminDeleteGroup,
  adminAddGroupMember,
  adminRemoveGroupMember,
  adminFetchPaypalTransactions,
  adminFetchWatches, adminCreateWatch, adminDeleteWatch, adminToggleWatch,
  adminWatchMakes, adminWatchModels, adminWatchPreview,
} from '../api.js'
import BackButton from '../components/BackButton.jsx'

const TABS = [
  { id: 'stats',    icon: '📊', label: 'סטטיסטיקות' },
  { id: 'activity', icon: '🕐', label: 'לוג פעילות' },
  { id: 'payments', icon: '💳', label: 'הזמנות' },
  { id: 'packages', icon: '⭐', label: 'מנויים' },
  { id: 'grants',   icon: '🎁', label: 'הטבות מנהל' },
  { id: 'users',    icon: '👥', label: 'משתמשים' },
  { id: 'groups',   icon: '👥', label: 'קבוצות' },
  { id: 'features', icon: '⭐', label: 'פיצ\'רים' },
  { id: 'promo',    icon: '🎉', label: 'מבצעי הצטרפות' },
  { id: 'broadcast',icon: '📢', label: 'שידור' },
  { id: 'settings', icon: '⚙️', label: 'הגדרות' },
  { id: 'tickets',  icon: '🎫', label: 'טיקטים' },
  { id: 'watches',  icon: '🔔', label: 'מעקב יד2' },
]

export default function AdminPage({ user, onBack }) {
  const [tab, setTab] = useState('stats')

  return (
    <div className="page">
      {onBack && <BackButton onClick={onBack} />}
      <div className="page-title">🛠 פאנל ניהול</div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 6,
        marginBottom: 18,
      }}>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
              padding: '9px 4px 7px', border: 'none', borderRadius: 10, cursor: 'pointer',
              background: tab === t.id ? 'var(--btn)' : 'var(--bg2)',
              color: tab === t.id ? 'var(--btn-text)' : 'var(--hint)',
              fontSize: 10, fontWeight: tab === t.id ? 600 : 400,
              transition: 'background 0.15s',
            }}
          >
            <span style={{ fontSize: 20, lineHeight: 1 }}>{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </div>
      {tab === 'stats'    && <StatsTab />}
      {tab === 'activity' && <ActivityTab />}
      {tab === 'payments' && <PaymentsTab />}
      {tab === 'packages' && <PackagesTab />}
      {tab === 'grants'   && <AdminGrantsTab />}
      {tab === 'users'     && <UsersTab />}
      {tab === 'groups'    && <GroupsTab />}
      {tab === 'features'  && <FeaturesTab />}
      {tab === 'promo'     && <PromoTab />}
      {tab === 'broadcast' && <BroadcastTab />}
      {tab === 'settings'  && <SettingsTab />}
      {tab === 'tickets'   && <TicketsTab />}
      {tab === 'watches'   && <WatchesTab />}
    </div>
  )
}

function StatCard({ value, label, sub, accent }) {
  return (
    <div style={{
      background: 'var(--bg2)', borderRadius: 12, padding: '12px 14px',
      borderRight: accent ? `3px solid ${accent}` : undefined,
    }}>
      <div style={{ fontSize: 22, fontWeight: 800, color: accent || 'var(--text)', lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', marginTop: 3 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--hint)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>{title}</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>{children}</div>
    </div>
  )
}

function StatsTab() {
  const [stats, setStats] = useState(null)
  useEffect(() => { adminFetchStats().then(setStats).catch(() => {}) }, [])
  if (!stats) return <div className="loading"></div>

  return (
    <div>
      <Section title="משתמשים">
        <StatCard value={stats.total_users}   label="סה״כ משתמשים" />
        <StatCard value={stats.active_week}   label="פעילים השבוע" accent="#38a169" />
        <StatCard value={stats.new_today}     label="חדשים היום"   sub={`${stats.new_week} השבוע`} accent="#38bdf8" />
        <StatCard value={stats.blocked_users} label="חסומים"       accent={stats.blocked_users > 0 ? '#e53e3e' : undefined} />
      </Section>

      <Section title="מנויים">
        <StatCard value={stats.subscribers}   label="מנויים פעילים" accent="#a855f7" />
        <StatCard value={stats.unlimited}     label="ללא הגבלה"     accent="#38bdf8" />
        <StatCard
          value={stats.expiring_soon}
          label="פגים ב-7 ימים"
          accent={stats.expiring_soon > 0 ? '#d69e2e' : undefined}
        />
        <StatCard value={stats.pending_payments} label="תשלומים ממתינים" accent={stats.pending_payments > 0 ? '#f59e0b' : undefined} />
      </Section>

      <Section title="חיפושים">
        <StatCard value={stats.searches_today} label="היום"    accent="#38a169" />
        <StatCard value={stats.searches_week}  label="השבוע" />
        <StatCard value={stats.total_searches} label="סה״כ כל הזמנים" />
        <StatCard value={stats.active_month}   label="פעילים החודש" />
      </Section>

      <Section title="קודים וטיקטים">
        <StatCard value={stats.active_codes}  label="קודים פעילים"  sub={`${stats.used_codes}/${stats.total_codes} נוצלו`} />
        <StatCard value={stats.tickets_open}  label="טיקטים פתוחים" accent={stats.tickets_open > 0 ? '#f59e0b' : undefined} />
      </Section>

      {stats.top_users?.length > 0 && (
        <div style={{ marginBottom: 18 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--hint)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
            🏆 מחפשים מובילים
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {stats.top_users.map((u, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                background: 'var(--bg2)', borderRadius: 10, padding: '8px 14px',
              }}>
                <span style={{ fontSize: 13 }}>
                  <span style={{ color: 'var(--hint)', marginLeft: 6 }}>#{i + 1}</span> {u.name}
                </span>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>{u.searches} 🔍</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function ActivityTab() {
  const [log, setLog] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(false)

  function load() { adminFetchActivity(100).then(setLog).catch(() => {}) }
  useEffect(() => { load() }, [])
  useEffect(() => {
    if (!autoRefresh) return
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [autoRefresh])

  function fmtTime(ts) { return fmtTimeShort(ts) }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)' }}>{log ? `${log.length} אירועים אחרונים` : ''}</div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label style={{ fontSize: 12, color: 'var(--hint)', display: 'flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
            <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} />
            רענון אוטומטי
          </label>
          <button
            className="btn"
            style={{ width: 'auto', padding: '4px 12px', marginTop: 0, fontSize: 12 }}
            onClick={load}
          >
            🔄
          </button>
        </div>
      </div>
      {!log && <div className="loading"></div>}
      {log && log.length === 0 && (
        <div style={{ color: 'var(--hint)', textAlign: 'center', padding: 24 }}>אין פעילות עדיין</div>
      )}
      {log && log.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {log.map(item => (
            <div key={item.id} style={{
              background: 'var(--card-bg, rgba(255,255,255,0.05))',
              borderRadius: 10,
              padding: '8px 12px',
              display: 'flex',
              gap: 10,
              alignItems: 'flex-start',
            }}>
              <span style={{ fontSize: 18, lineHeight: 1.3, flexShrink: 0 }}>{item.icon}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, wordBreak: 'break-word' }}>{item.description}</div>
                {item.username && (
                  <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 2 }}>{item.username}</div>
                )}
              </div>
              <div style={{ fontSize: 11, color: 'var(--hint)', flexShrink: 0, textAlign: 'left', whiteSpace: 'nowrap' }}>
                {fmtTime(item.created_at)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const DEFAULT_PKG_FEATURES = [
  'נתוני רכב מלאים — שנה, דגם, בעלות, טסט, ק״מ',
  'מחיר שוק Yad2 — השוואת מחירים עדכנית',
  'הורדת דוח PDF מפורט',
  'העתקת דוח לשיתוף',
  'הערות אישיות לכל רכב — נשמרות ומופיעות בדוח',
  'היסטוריית חיפושים אישית',
  'גישה לכל תכונות המנוי הקיימות והעתידיות',
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
      })
      setPkgs(fresh)
      setAdding(false)
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function deletePkg(id) {
    window.Telegram?.WebApp?.showConfirm('למחוק מנוי?', async (ok) => {
      if (!ok) return
      await adminDeletePackage(id)
      setPkgs(await adminFetchPackages())
    })
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
            onClick={() => { setEditing(freePkg); setForm({ label: freePkg.label, searches: '0', price: '0', image_url: freePkg.image_url || '', duration_months: '1', features: normalizeFeatures(freePkg.features), chips: freePkg.chips?.length ? freePkg.chips : getDefaultChips(freePkg) }) }}
          >✏️ ערוך</button>
        </div>
      )}

      <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 10 }}>
        גרור ⠿ לשינוי סדר תצוגה · 1 = ראשון
      </div>
      {paidPkgs.map((pkg, idx) => {
        const desc = pkg.searches === -1 ? 'ללא הגבלה' : `${pkg.searches} חיפושים`
        const isDragging = dragIdx === idx
        return (
          <div
            key={pkg.id}
            draggable={!reordering}
            onDragStart={() => setDragIdx(idx)}
            onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move' }}
            onDrop={() => { if (dragIdx !== null) movePackage(dragIdx, idx); setDragIdx(null) }}
            onDragEnd={() => setDragIdx(null)}
            className="card"
            style={{
              opacity: isDragging ? 0.45 : 1,
              cursor: reordering ? 'wait' : 'grab',
              transition: 'opacity 0.15s',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, flex: 1, minWidth: 0 }}>
                <span
                  style={{ fontSize: 20, color: 'var(--hint)', lineHeight: 1.2, cursor: 'grab', userSelect: 'none', flexShrink: 0 }}
                  title="גרור לשינוי סדר"
                >⠿</span>
                <span style={{
                  fontSize: 11, fontWeight: 700, color: 'var(--hint)',
                  background: 'var(--bg)', borderRadius: 6, padding: '2px 7px', flexShrink: 0,
                }}>{idx + 1}</span>
                <div>
                  <div className="card-title">{pkg.label}</div>
                  <div className="card-subtitle">{desc} · ₪{pkg.price}</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                <button
                  className="btn"
                  style={{ width: 'auto', padding: '4px 8px', marginTop: 0, fontSize: 12 }}
                  disabled={idx === 0 || reordering}
                  onClick={() => movePackage(idx, idx - 1)}
                  title="הזז למעלה"
                >↑</button>
                <button
                  className="btn"
                  style={{ width: 'auto', padding: '4px 8px', marginTop: 0, fontSize: 12 }}
                  disabled={idx === paidPkgs.length - 1 || reordering}
                  onClick={() => movePackage(idx, idx + 1)}
                  title="הזז למטה"
                >↓</button>
                <button className="btn" style={{ width: 'auto', padding: '6px 12px', marginTop: 0, fontSize: 13 }}
                  onClick={() => { setEditing(pkg); setForm({ label: pkg.label, searches: String(pkg.searches), price: String(pkg.price), image_url: pkg.image_url || '', duration_months: String(pkg.duration_months ?? 1), features: normalizeFeatures(pkg.features), chips: pkg.chips?.length ? pkg.chips : getDefaultChips(pkg) }) }}>
                  ✏️
                </button>
                <button className="btn btn-danger" style={{ width: 'auto', padding: '6px 12px', marginTop: 0, fontSize: 13 }}
                  onClick={() => deletePkg(pkg.id)}>
                  🗑
                </button>
              </div>
            </div>
          </div>
        )
      })}
      <button className="btn btn-success" onClick={() => { setAdding(true); setForm({ label: '', searches: '', price: '', image_url: '', duration_months: '1', features: normalizeFeatures([]), chips: [] }) }}>
        ➕ הוסף מנוי
      </button>

      {editing && (
        <PackageModal
          title="✏️ עריכת מנוי"
          form={form} setForm={setForm}
          saving={saving} onSave={saveEdit} onClose={() => setEditing(null)}
          suggestions={allChipsPool}
        />
      )}
      {adding && (
        <PackageModal
          title="➕ מנוי חדש"
          form={form} setForm={setForm}
          saving={saving} onSave={saveAdd} onClose={() => setAdding(false)}
          suggestions={allChipsPool}
        />
      )}
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
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--hint)', marginBottom: 8 }}>
        ציפים
        {isFree && <span style={{ fontWeight: 400, marginRight: 6 }}>· הציפ "X חיפושים נותרו" מוצג אוטומטית</span>}
      </div>

      {/* Current chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
        {chips.map(chip => (
          <span key={chip} style={{
            display: 'inline-flex', alignItems: 'center', gap: 5,
            fontSize: 12, padding: '4px 10px',
            background: 'var(--btn)22', border: '1px solid var(--btn)44',
            borderRadius: 20, color: 'var(--text)',
          }}>
            {chip}
            <button
              type="button"
              onClick={() => removeChip(chip)}
              style={{ background: 'none', border: 'none', color: 'var(--hint)', cursor: 'pointer', fontSize: 13, padding: 0, lineHeight: 1 }}
            >✕</button>
          </span>
        ))}
      </div>

      {/* Suggestions from other packages */}
      {availableSuggestions.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 11, color: 'var(--hint)', marginBottom: 5 }}>בחר מהרשימה:</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
            {availableSuggestions.map(s => (
              <button
                key={s}
                type="button"
                onClick={() => onChange([...chips, s])}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  fontSize: 12, padding: '3px 9px',
                  background: 'transparent', border: '1px dashed var(--btn)66',
                  borderRadius: 20, color: 'var(--hint)', cursor: 'pointer',
                }}
              >+ {s}</button>
            ))}
          </div>
        </div>
      )}

      {/* Add new */}
      <div style={{ display: 'flex', gap: 6 }}>
        <input
          className="input"
          style={{ flex: 1, marginBottom: 0, fontSize: 13 }}
          placeholder='לדוגמה: 💳 חד-פעמי'
          value={newChip}
          onChange={e => setNewChip(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addChip()}
        />
        <button
          type="button"
          className="btn"
          style={{ width: 'auto', padding: '0 14px', marginTop: 0, fontSize: 13, flexShrink: 0 }}
          disabled={!newChip.trim()}
          onClick={addChip}
        >+</button>
      </div>
    </div>
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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">{title}</div>
        <input
          className="input"
          placeholder="שם המנוי"
          value={form.label}
          onChange={e => setForm(f => ({ ...f, label: e.target.value }))}
        />
        {form.searches !== '0' && (
          <>
            <input
              className="input"
              placeholder="חיפושים (-1 לבלתי מוגבל)"
              type="number"
              value={form.searches}
              onChange={e => setForm(f => ({ ...f, searches: e.target.value }))}
            />
            <input
              className="input"
              placeholder="מחיר (₪)"
              type="number"
              value={form.price}
              onChange={e => setForm(f => ({ ...f, price: e.target.value }))}
            />
          </>
        )}
        {parseInt(form.searches) === -1 && (
          <input
            className="input"
            placeholder="משך בחודשים (ברירת מחדל: 1)"
            type="number"
            min="1"
            value={form.duration_months ?? '1'}
            onChange={e => setForm(f => ({ ...f, duration_months: e.target.value }))}
          />
        )}

        {form.image_url ? (
          <div style={{ position: 'relative', marginBottom: 8 }}>
            <img
              src={form.image_url}
              alt="תצוגה מקדימה"
              style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 8, display: 'block' }}
              onError={e => { e.target.style.display = 'none' }}
            />
            <button
              onClick={() => setForm(f => ({ ...f, image_url: '' }))}
              style={{
                position: 'absolute', top: 6, left: 6,
                background: 'rgba(0,0,0,0.55)', color: '#fff',
                border: 'none', borderRadius: '50%', width: 28, height: 28,
                fontSize: 14, cursor: 'pointer', lineHeight: 1,
              }}
            >✕</button>
          </div>
        ) : (
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1, marginTop: 0, fontSize: 13 }}
              disabled={compressing}
              onClick={() => fileRef.current?.click()}
            >
              {compressing ? '⏳ מכווץ...' : '📷 העלאה מהמכשיר'}
            </button>
            <input
              className="input"
              style={{ flex: 2, marginBottom: 0 }}
              placeholder="או הדבק כתובת URL"
              value={form.image_url}
              onChange={e => setForm(f => ({ ...f, image_url: e.target.value }))}
            />
          </div>
        )}
        <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFile} />

        {/* Chips */}
        <ChipsEditor chips={form.chips || []} onChange={chips => setForm(f => ({ ...f, chips }))} isFree={form.searches === '0'} suggestions={suggestions} />

        {/* Features */}
        <div style={{ marginTop: 4, marginBottom: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--hint)', marginBottom: 8 }}>
            תכונות המנוי
            <span style={{ fontWeight: 400, marginRight: 6 }}>· ✅ קיים &nbsp; ✗ לא קיים &nbsp; ריק = מוסתר</span>
          </div>

          {/* Active features — ordered list with ↑↓ */}
          {activeFeatures.map((item, idx) => {
            const state = item.included ? 'included' : 'excluded'
            return (
              <div key={item.text} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 7 }}>
                {/* Reorder */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 1, flexShrink: 0 }}>
                  <button type="button" onClick={() => moveFeature(idx, -1)} disabled={idx === 0}
                    style={{ width: 20, height: 18, border: '1px solid rgba(255,255,255,0.15)', borderRadius: 4, background: 'transparent', color: idx === 0 ? 'rgba(255,255,255,0.15)' : 'var(--hint)', cursor: idx === 0 ? 'default' : 'pointer', fontSize: 10, lineHeight: 1, padding: 0 }}>▲</button>
                  <button type="button" onClick={() => moveFeature(idx, 1)} disabled={idx === activeFeatures.length - 1}
                    style={{ width: 20, height: 18, border: '1px solid rgba(255,255,255,0.15)', borderRadius: 4, background: 'transparent', color: idx === activeFeatures.length - 1 ? 'rgba(255,255,255,0.15)' : 'var(--hint)', cursor: idx === activeFeatures.length - 1 ? 'default' : 'pointer', fontSize: 10, lineHeight: 1, padding: 0 }}>▼</button>
                </div>
                {/* Toggle buttons */}
                <div style={{ display: 'flex', gap: 3, flexShrink: 0 }}>
                  <button type="button" onClick={() => setFeatureState(item.text, 'included')}
                    style={{ width: 28, height: 28, border: '1.5px solid', borderColor: state === 'included' ? '#38a169' : 'rgba(255,255,255,0.2)', borderRadius: 7, background: state === 'included' ? '#38a16922' : 'transparent', color: state === 'included' ? '#38a169' : 'var(--hint)', cursor: 'pointer', fontSize: 14, lineHeight: 1, fontWeight: 700 }} title="קיים">✓</button>
                  <button type="button" onClick={() => setFeatureState(item.text, 'excluded')}
                    style={{ width: 28, height: 28, border: '1.5px solid', borderColor: state === 'excluded' ? '#e53e3e' : 'rgba(255,255,255,0.2)', borderRadius: 7, background: state === 'excluded' ? '#e53e3e22' : 'transparent', color: state === 'excluded' ? '#e53e3e' : 'var(--hint)', cursor: 'pointer', fontSize: 14, lineHeight: 1, fontWeight: 700 }} title="לא קיים">✗</button>
                </div>
                <span style={{ fontSize: 13, flex: 1, lineHeight: 1.4 }}>{item.text}</span>
                <button type="button" onClick={() => removeFeature(item.text)}
                  style={{ background: 'none', border: 'none', color: 'var(--hint)', cursor: 'pointer', fontSize: 15, padding: '0 2px', flexShrink: 0 }} title="הסר מהרשימה">✕</button>
              </div>
            )
          })}

          {/* Inactive defaults — click to add */}
          {inactiveDefaults.length > 0 && (
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', marginTop: 8, paddingTop: 8 }}>
              <div style={{ fontSize: 11, color: 'var(--hint)', marginBottom: 6 }}>לחץ להוספה לרשימה:</div>
              {inactiveDefaults.map(feat => (
                <div key={feat} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <div style={{ display: 'flex', gap: 3, flexShrink: 0 }}>
                    <button type="button" onClick={() => setFeatureState(feat, 'included')}
                      style={{ width: 28, height: 28, border: '1.5px solid rgba(255,255,255,0.15)', borderRadius: 7, background: 'transparent', color: 'var(--hint)', cursor: 'pointer', fontSize: 14, lineHeight: 1, fontWeight: 700 }} title="הוסף כקיים">✓</button>
                    <button type="button" onClick={() => setFeatureState(feat, 'excluded')}
                      style={{ width: 28, height: 28, border: '1.5px solid rgba(255,255,255,0.15)', borderRadius: 7, background: 'transparent', color: 'var(--hint)', cursor: 'pointer', fontSize: 14, lineHeight: 1, fontWeight: 700 }} title="הוסף כלא קיים">✗</button>
                  </div>
                  <span style={{ fontSize: 13, color: 'var(--hint)', opacity: 0.5, flex: 1, lineHeight: 1.4 }}>{feat}</span>
                </div>
              ))}
            </div>
          )}

          {/* Add new custom feature */}
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <input
              className="input"
              style={{ flex: 1, marginBottom: 0, fontSize: 13 }}
              placeholder="הוסף תכונה חדשה..."
              value={newFeature}
              onChange={e => setNewFeature(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addCustomFeature()}
            />
            <button
              type="button"
              className="btn"
              style={{ width: 'auto', padding: '0 14px', marginTop: 0, fontSize: 13, flexShrink: 0 }}
              disabled={!newFeature.trim()}
              onClick={addCustomFeature}
            >+</button>
          </div>
        </div>

        <button className="btn" disabled={saving} onClick={onSave}>{saving ? '...' : 'שמור'}</button>
        <button className="btn btn-secondary" style={{ marginTop: 8 }} onClick={onClose}>ביטול</button>
      </div>
    </div>
  )
}

function grantTypeLabel(searches) {
  if (searches === 0) return '0 חיפושים (מנוי חינם)'
  if (searches === -1) return 'מנוי חודשי · 30 יום'
  if (searches === -2) return 'גישה חופשית · ללא הגבלה'
  return `${searches} חיפושים`
}

function AdminGrantsTab() {
  const [grants, setGrants] = useState(null)
  const [editing, setEditing] = useState(null)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ label: '', searches: '' })
  const [saving, setSaving] = useState(false)
  const [dragIdx, setDragIdx] = useState(null)
  const [reordering, setReordering] = useState(false)
  const [codesOpen, setCodesOpen] = useState(false)
  const [giftOpen, setGiftOpen]   = useState(false)

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
    window.Telegram?.WebApp?.showConfirm('למחוק הטבה?', async (ok) => {
      if (!ok) return
      await adminDeleteGrant(id)
      setGrants(await adminFetchGrants())
    })
  }

  if (!grants) return <div className="loading"></div>

  return (
    <div>
      <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 10, lineHeight: 1.5 }}>
        הטבות שמנהל יכול לתת למשתמש בעריכת משתמש. גרור ⠿ לשינוי סדר · 1 = ראשון.
        <br />
        ערכי חיפושים: 0=מנוי חינם, -1=חודשי, -2=גישה חופשית, מספר חיובי=הוספת חיפושים.
      </div>
      {grants.map((g, idx) => {
        const isDragging = dragIdx === idx
        return (
          <div
            key={g.id}
            draggable={!reordering}
            onDragStart={() => setDragIdx(idx)}
            onDragOver={e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move' }}
            onDrop={() => { if (dragIdx !== null) moveGrant(dragIdx, idx); setDragIdx(null) }}
            onDragEnd={() => setDragIdx(null)}
            className="card"
            style={{ opacity: isDragging ? 0.45 : 1, cursor: reordering ? 'wait' : 'grab' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: 20, color: 'var(--hint)', cursor: 'grab', userSelect: 'none' }}>⠿</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--hint)', background: 'var(--bg)', borderRadius: 6, padding: '2px 7px' }}>{idx + 1}</span>
                <div>
                  <div className="card-title">{g.label}</div>
                  <div className="card-subtitle">{grantTypeLabel(g.searches)}</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                <button className="btn" style={{ width: 'auto', padding: '4px 8px', marginTop: 0, fontSize: 12 }}
                  disabled={idx === 0 || reordering} onClick={() => moveGrant(idx, idx - 1)}>↑</button>
                <button className="btn" style={{ width: 'auto', padding: '4px 8px', marginTop: 0, fontSize: 12 }}
                  disabled={idx === grants.length - 1 || reordering} onClick={() => moveGrant(idx, idx + 1)}>↓</button>
                <button className="btn" style={{ width: 'auto', padding: '6px 12px', marginTop: 0, fontSize: 13 }}
                  onClick={() => { setEditing(g); setForm({ label: g.label, searches: String(g.searches) }) }}>✏️</button>
                <button className="btn btn-danger" style={{ width: 'auto', padding: '6px 12px', marginTop: 0, fontSize: 13 }}
                  onClick={() => deleteGrant(g.id)}>🗑</button>
              </div>
            </div>
          </div>
        )
      })}
      <button className="btn btn-success" onClick={() => { setAdding(true); setForm({ label: '', searches: '' }) }}>
        ➕ הוסף הטבה
      </button>

      {/* Gift all section */}
      <div style={{ marginTop: 16, borderTop: '1px solid var(--border, rgba(255,255,255,0.1))', paddingTop: 16 }}>
        <button
          onClick={() => setGiftOpen(o => !o)}
          style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 0, color: 'var(--text)' }}
        >
          <span style={{ fontSize: 15, fontWeight: 700 }}>🎁 הענק מתנה לכל המשתמשים</span>
          <span style={{ fontSize: 12, color: 'var(--hint)' }}>{giftOpen ? '▲' : '▼'}</span>
        </button>
        {giftOpen && <GiftAllSection onDone={() => setGiftOpen(false)} />}
      </div>

      {/* Codes section */}
      <div style={{ marginTop: 16, borderTop: '1px solid var(--border, rgba(255,255,255,0.1))', paddingTop: 16 }}>
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
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">{title}</div>
        <input className="input" placeholder="שם ההטבה" value={form.label} onChange={e => setForm(f => ({ ...f, label: e.target.value }))} />
        <input className="input" placeholder="חיפושים (0=חינם, -1=חודשי, -2=חופשי)" type="number" value={form.searches} onChange={e => setForm(f => ({ ...f, searches: e.target.value }))} />
        <div style={{ fontSize: 11, color: 'var(--hint)', marginBottom: 12, lineHeight: 1.4 }}>
          0 = מנוי חינם · -1 = מנוי חודשי · -2 = גישה חופשית · מספר חיובי = הוספת חיפושים
        </div>
        <button className="btn" disabled={saving || !form.label.trim()} onClick={onSave}>{saving ? '...' : 'שמור'}</button>
        <button className="btn btn-secondary" style={{ marginTop: 8 }} onClick={onClose}>ביטול</button>
      </div>
    </div>
  )
}

const STATUS_META = {
  intent:    { label: 'ממתין לתשלום', color: '#888' },
  created:   { label: 'ממתין לתשלום', color: '#888' },
  approved:  { label: 'אושר',    color: '#2196F3' },
  captured:  { label: 'נגבה',    color: '#00bcd4' },
  completed: { label: 'הושלם',   color: '#4caf50' },
  failed:    { label: 'נכשל',    color: '#f44336' },
  expired:   { label: 'פג תוקף', color: '#ff9800' },
  declined:  { label: 'נדחה',    color: '#f44336' },
  cancelled:        { label: 'בוטל',               color: '#ff9800' },
  user_cancelled:   { label: 'בוטל ע״י משתמש',    color: '#ff9800' },
  admin_approved:   { label: 'אושר ע״י מנהל',  color: '#4caf50' },
  admin_cancelled:  { label: 'בוטל ע״י מנהל',  color: '#ff9800' },
}

function PaypalTransactionRow({ tx, onRefresh }) {
  const [open, setOpen] = useState(false)
  const [working, setWorking] = useState(false)
  const meta = STATUS_META[tx.status] || { label: tx.status, color: '#888' }
  const canAct = ['intent', 'created', 'cancelled'].includes(tx.status)

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

  return (
    <div
      style={{ background: 'var(--card-bg, rgba(255,255,255,0.05))', borderRadius: 12, marginBottom: 8, overflow: 'hidden', cursor: 'pointer' }}
      onClick={() => setOpen(o => !o)}
    >
      <div style={{ padding: '10px 14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
          <span style={{ fontFamily: 'monospace', fontSize: 13, fontWeight: 700, color: 'var(--accent, #2196F3)' }}>#{tx.ref}</span>
          <span style={{ background: meta.color, color: '#fff', borderRadius: 6, padding: '2px 8px', fontSize: 11, fontWeight: 700 }}>{meta.label}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
          <span style={{ fontWeight: 600 }}>{tx.label}</span>
          <span style={{ color: '#4caf50', fontWeight: 700 }}>₪{tx.amount}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3, fontSize: 11, color: 'var(--hint)' }}>
          <span>{tx.username ? `@${tx.username}` : tx.full_name || `משתמש ${tx.user_id}`}</span>
          <span>{fmtDateTime(tx.created_at)}</span>
        </div>
      </div>
      {open && (
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', padding: '10px 14px', fontSize: 12 }} onClick={e => e.stopPropagation()}>
          <div style={{ marginBottom: 4 }}><span style={{ color: 'var(--hint)' }}>PayPal Order ID: </span><span style={{ fontFamily: 'monospace', wordBreak: 'break-all', fontSize: 11 }}>{tx.paypal_order_id || '—'}</span></div>
          <div style={{ marginBottom: 4 }}><span style={{ color: 'var(--hint)' }}>חיפושים: </span>{tx.searches === -1 ? '♾️ ללא הגבלה' : tx.searches}</div>
          <div style={{ marginBottom: 4 }}><span style={{ color: 'var(--hint)' }}>עדכון אחרון: </span>{fmtDateTime(tx.updated_at)}</div>
          {tx.error && <div style={{ marginTop: 6, color: '#f44336', wordBreak: 'break-all' }}>⚠️ {tx.error}</div>}
          {canAct && (
            <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
              <button
                onClick={approve}
                disabled={working}
                style={{ flex: 1, padding: '7px 0', background: '#4caf50', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: working ? 'default' : 'pointer', opacity: working ? 0.6 : 1 }}
              >✅ אישור מנהל</button>
              <button
                onClick={cancel}
                disabled={working}
                style={{ flex: 1, padding: '7px 0', background: '#f44336', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: working ? 'default' : 'pointer', opacity: working ? 0.6 : 1 }}
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
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)' }}>{txs ? `${txs.length} עסקאות` : ''}</div>
        <button className="btn" style={{ width: 'auto', padding: '4px 12px', marginTop: 0, fontSize: 12 }} onClick={load}>🔄</button>
      </div>
      {!txs && <div className="loading"></div>}
      {txs?.length === 0 && <div style={{ color: 'var(--hint)', textAlign: 'center', padding: 24 }}>אין עסקאות עדיין</div>}
      {txs?.map(tx => <PaypalTransactionRow key={tx.id} tx={tx} onRefresh={load} />)}
    </div>
  )
}

function CodesSection() {
  const [codes, setCodes] = useState(null)
  const [form, setForm] = useState({ searches: 50, unlimited: false, single_use: true, monthly: false })
  const [creating, setCreating] = useState(false)

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
    window.Telegram?.WebApp?.showConfirm(`למחוק את הקוד ${code}?`, async ok => {
      if (!ok) return
      try { await adminDeleteCode(code); load() }
      catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    })
  }

  function copyCode(code) {
    navigator.clipboard?.writeText(code).catch(() => {})
    window.Telegram?.WebApp?.showAlert(`✅ הועתק:\n${code}`)
  }

  if (!codes) return <div className="loading"></div>

  return (
    <div style={{ marginTop: 14 }}>
      {/* Create code */}
      <div style={{ background: 'var(--card-bg, rgba(255,255,255,0.05))', borderRadius: 12, padding: '12px 14px', marginBottom: 14 }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>➕ צור קוד חדש</div>
        <input
          className="input"
          type="number"
          min="1"
          placeholder="כמות חיפושים"
          value={form.searches}
          onChange={e => setForm(f => ({ ...f, searches: parseInt(e.target.value) || 50 }))}
          style={{ marginBottom: 8 }}
          disabled={form.unlimited}
        />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
          {[['unlimited', '♾️ ללא הגבלה'], ['monthly', '📅 חודשי'], ['single_use', '1️⃣ חד-פעמי']].map(([key, label]) => (
            <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 13, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={form[key]}
                onChange={e => setForm(f => ({ ...f, [key]: e.target.checked, ...(key === 'unlimited' ? { monthly: false } : {}) }))}
              />
              {label}
            </label>
          ))}
        </div>
        <button className="btn" disabled={creating} onClick={createCode} style={{ marginTop: 0 }}>
          {creating ? '⏳...' : '➕ צור קוד'}
        </button>
      </div>

      {/* Code list */}
      <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8 }}>{codes.length} קודים</div>
      {codes.map(c => {
        const used = c.used_by != null
        const expired = c.expires && new Date(c.expires) < new Date()
        const status = used ? '✅ נוצל' : expired ? '⏰ פג' : '🟢 פעיל'
        const desc = c.unlimited ? (c.monthly ? '📅 חודשי' : '♾️ ללא הגבלה') : `${c.searches} חיפושים`
        return (
          <div key={c.code} style={{ background: 'var(--card-bg, rgba(255,255,255,0.05))', borderRadius: 10, padding: '10px 12px', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: 14, letterSpacing: 1 }}>{c.code}</div>
              <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 2 }}>{desc} · {status}{c.single_use ? ' · חד-פעמי' : ''}</div>
            </div>
            <button
              className="btn"
              style={{ width: 'auto', padding: '4px 10px', marginTop: 0, fontSize: 12 }}
              onClick={() => copyCode(c.code)}
            >
              📋
            </button>
            <button
              className="btn btn-danger"
              style={{ width: 'auto', padding: '4px 10px', marginTop: 0, fontSize: 12 }}
              onClick={() => deleteCode(c.code)}
            >
              🗑️
            </button>
          </div>
        )
      })}
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
        background: giftType === type ? 'var(--button-color, #2196F3)' : 'var(--secondary-bg, rgba(255,255,255,0.08))',
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
  if (u.blocked) return { label: 'חסום', color: '#e53e3e', bg: '#e53e3e18' }
  if (u.is_subscriber || u.searches_left === -1) return { label: 'מנוי', color: '#38bdf8', bg: '#38bdf818' }
  if (u.searches_left > 0) return { label: 'חינם', color: '#38a169', bg: '#38a16918' }
  return { label: 'אזל', color: '#d69e2e', bg: '#d69e2e18' }
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

function UserCard({ u, expanded, onToggle, onEdit, onMessage, onReload }) {
  const [blocking, setBlocking] = useState(false)
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

  return (
    <div style={{
      background: 'var(--bg2)', borderRadius: 14, marginBottom: 8, overflow: 'hidden',
      border: u.blocked ? '1px solid #e53e3e33' : u.is_subscriber ? '1px solid #38bdf822' : '1px solid transparent',
      transition: 'border-color 0.15s',
    }}>
      {/* Collapsed header */}
      <div
        style={{ display: 'flex', gap: 10, padding: '12px 13px', alignItems: 'center', cursor: 'pointer', userSelect: 'none' }}
        onClick={() => onToggle(u.user_id)}
      >
        {/* Avatar */}
        <div style={{
          width: 44, height: 44, borderRadius: '50%', flexShrink: 0,
          background: `${st.color}18`,
          border: `2.5px solid ${st.color}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 14, fontWeight: 800, color: st.color,
        }}>
          {initials}
        </div>

        {/* Main info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, flexWrap: 'wrap' }}>
            <span style={{
              fontSize: 14, fontWeight: 700, color: 'var(--text)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 140,
            }}>{displayName}</span>
            <span style={{
              fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20, flexShrink: 0,
              background: st.bg, color: st.color,
            }}>{st.label}</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--hint)', display: 'flex', gap: 8 }}>
            <span>🔍 {u.searches_done} נעשו</span>
            <span>·</span>
            <span style={{ color: u.searches_left === 0 ? '#d69e2e' : 'var(--hint)' }}>{left} נותרו</span>
            {u.last_seen && <><span>·</span><span>{relativeTime(u.last_seen)}</span></>}
          </div>
        </div>

        {/* Chevron */}
        <span style={{ color: 'var(--hint)', fontSize: 11, flexShrink: 0, transition: 'transform 0.15s', display: 'inline-block', transform: expanded ? 'rotate(180deg)' : 'none' }}>▼</span>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.07)', padding: '12px 13px' }}>

          {/* Stats mini-grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 7, marginBottom: 10 }}>
            {[
              { label: 'נעשו', value: u.searches_done, color: '#38bdf8' },
              { label: 'נותרו', value: left, color: st.color },
              { label: 'מזהה', value: u.user_id, mono: true },
            ].map(({ label, value, color, mono }) => (
              <div key={label} style={{
                background: 'var(--bg)', borderRadius: 9, padding: '7px 6px', textAlign: 'center',
              }}>
                <div style={{
                  fontWeight: 700,
                  fontSize: mono ? 11 : 15,
                  color: color || 'var(--text)',
                  fontFamily: mono ? 'monospace' : undefined,
                  wordBreak: 'break-all',
                }}>{value}</div>
                <div style={{ fontSize: 10, color: 'var(--hint)', marginTop: 2 }}>{label}</div>
              </div>
            ))}
          </div>

          {/* Meta info */}
          <div style={{
            background: 'var(--bg)', borderRadius: 9, padding: '9px 11px',
            fontSize: 11, color: 'var(--hint)', marginBottom: 12,
            display: 'flex', flexDirection: 'column', gap: 4,
          }}>
            {u.member_id != null && (
              <div>🏷 מס׳ חבר: <span style={{ fontFamily: 'monospace', color: 'var(--text)', fontWeight: 600 }}>#{u.member_id}</span></div>
            )}
            {u.first_seen && <div>📅 הצטרף: <span style={{ color: 'var(--text)' }}>{fmtDateIL(u.first_seen)}</span></div>}
            {u.last_seen  && <div>👁 נראה לאחרונה: <span style={{ color: 'var(--text)' }}>{fmtDateTime(u.last_seen)}</span></div>}
            {u.quota_expires && <div>⏰ פג תוקף: <span style={{ color: '#d69e2e', fontWeight: 600 }}>{u.quota_expires.slice(0, 10)}</span></div>}
            {u.channel && <div>📡 ערוץ: <span style={{ color: 'var(--text)' }}>{u.channel}</span></div>}
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: 7 }}>
            <button
              onClick={e => { e.stopPropagation(); onEdit(u) }}
              style={{
                flex: 1, padding: '9px 0', borderRadius: 9, border: 'none',
                background: 'var(--bg)', color: 'var(--text)', cursor: 'pointer', fontSize: 13, fontWeight: 600,
              }}
            >✏️ ערוך</button>
            <button
              onClick={e => { e.stopPropagation(); onMessage(u) }}
              style={{
                flex: 1, padding: '9px 0', borderRadius: 9, border: 'none',
                background: 'var(--bg)', color: 'var(--text)', cursor: 'pointer', fontSize: 13, fontWeight: 600,
              }}
            >💬 הודעה</button>
            <button
              onClick={toggleBlock}
              disabled={blocking}
              style={{
                flex: 1, padding: '9px 0', borderRadius: 9, border: 'none',
                background: u.blocked ? '#38a16918' : '#e53e3e18',
                color: u.blocked ? '#38a169' : '#e53e3e',
                cursor: blocking ? 'default' : 'pointer', fontSize: 12, fontWeight: 600,
                opacity: blocking ? 0.6 : 1,
              }}
            >{u.blocked ? '🔓 בטל חסימה' : '🚫 חסום'}</button>
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
    <div>
      {/* Search */}
      <input
        className="input"
        placeholder="חיפוש לפי שם / ID..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        style={{ marginBottom: 8, fontSize: 13 }}
      />

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 8, background: 'var(--bg)', borderRadius: 10, padding: 3 }}>
        {FILTERS.map(([id, label, statusLabel]) => {
          const count = id === 'all' ? users.length : users.filter(u => userStatus(u).label === statusLabel).length
          return (
            <button key={id} onClick={() => setFilter(id)} style={{
              flex: 1, padding: '5px 2px', fontSize: 10, borderRadius: 7, border: 'none',
              background: filter === id ? 'var(--bg2)' : 'transparent',
              color: filter === id ? 'var(--text)' : 'var(--hint)',
              cursor: 'pointer', fontWeight: filter === id ? 600 : 400,
            }}>
              {label}<br />
              <span style={{ fontSize: 11, opacity: 0.7 }}>{count}</span>
            </button>
          )
        })}
      </div>

      {/* Sort + count row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{ fontSize: 12, color: 'var(--hint)' }}>{sorted.length} משתמשים</span>
        <div style={{ display: 'flex', gap: 4 }}>
          {SORTS.map(([id, label]) => (
            <button key={id} onClick={() => setSort(id)} style={{
              padding: '4px 9px', fontSize: 11, borderRadius: 7, border: 'none', cursor: 'pointer',
              background: sort === id ? 'var(--btn)' : 'var(--bg)',
              color: sort === id ? 'var(--btn-text)' : 'var(--hint)',
              fontWeight: sort === id ? 600 : 400,
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
    </div>
  )
}

function GrantModal({ user, onClose, onDone }) {
  const [grants, setGrants] = useState(null)
  const [mode, setMode] = useState('grants') // 'grants' | 'custom' | 'history' | 'referrals'
  const [customAmount, setCustomAmount] = useState('')
  const [saving, setSaving] = useState(false)
  const [history, setHistory] = useState(null)
  const [referralData, setReferralData] = useState(null)
  const [pendingGrant, setPendingGrant] = useState(null)

  useEffect(() => { adminFetchGrants().then(setGrants).catch(() => {}) }, [])
  useEffect(() => {
    if (mode === 'history' && history === null) {
      adminFetchUserHistory(user.user_id).then(setHistory).catch(() => setHistory([]))
    }
    if (mode === 'referrals' && referralData === null) {
      adminFetchUserReferrals(user.user_id).then(setReferralData).catch(() => setReferralData({ referrals: [], count: 0, total_bonus: 0 }))
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
    ['history',   '📋', 'חיפושים'],
    ['referrals', '🤝', 'הפניות'],
  ]

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ padding: '18px 16px' }}>

        {/* Title */}
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 14, color: 'var(--text)' }}>
          עריכת {name}
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 16, background: 'var(--bg)', borderRadius: 10, padding: 3 }}>
          {TABS.map(([id, icon, label]) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              style={{
                flex: 1, padding: '6px 2px', fontSize: 10, borderRadius: 7, border: 'none',
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
                    border: selected ? '1px solid #7c3aed' : g.searches === 0 ? '1px solid #38a16944' : '1px solid rgba(255,255,255,0.08)',
                    background: selected ? '#7c3aed22' : g.searches === 0 ? '#38a16911' : 'var(--bg)',
                    cursor: 'pointer', opacity: saving ? 0.5 : 1,
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: 600, color: selected ? '#a78bfa' : g.searches === 0 ? '#38a169' : 'var(--text)' }}>{g.label}</span>
                  <span style={{ fontSize: 12, color: selected ? '#a78bfa' : 'var(--hint)' }}>{grantTypeLabel(g.searches)}</span>
                </button>
              )
            })}

            {user.is_subscriber && (
              <>
                <div style={{ height: 1, background: 'rgba(255,255,255,0.07)', margin: '4px 0' }} />
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
                    border: '1px solid #e53e3e44',
                    background: '#e53e3e11', cursor: 'pointer', opacity: saving ? 0.5 : 1,
                  }}
                >
                  <span style={{ fontSize: 13, color: '#e53e3e', fontWeight: 600 }}>🚫 הסר מנוי</span>
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

        {mode === 'history' && (
          <div>
            {history === null && <div className="loading"></div>}
            {history !== null && history.length === 0 && (
              <div style={{ color: 'var(--hint)', fontSize: 13, textAlign: 'center', padding: 12 }}>
                אין היסטוריית חיפושים
              </div>
            )}
            {history !== null && history.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {history.map((plate, i) => (
                  <span
                    key={i}
                    style={{
                      background: '#f5c518', color: '#111', fontWeight: 700,
                      borderRadius: 6, padding: '4px 10px', fontSize: 13, letterSpacing: 1,
                    }}
                  >
                    {plate}
                  </span>
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
                    borderRight: '3px solid #38a169',
                  }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{ref.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--hint)' }}>{ref.joined_at?.slice(0, 10)}</div>
                    </div>
                    <span style={{
                      background: '#38a16920', color: '#38a169',
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
    </div>
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

  return (
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
    </div>
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

  const STATUS_COLORS = { active: '#38a169', upcoming: '#d69e2e', expired: '#e53e3e' }
  const STATUS_LABELS = { active: '🟢 פעיל כעת', upcoming: '🟡 טרם התחיל', expired: '🔴 הסתיים' }
  const pStatus = promoStatus()

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18 }}>
        <div style={{ fontWeight: 700, fontSize: 17 }}>🎉 מבצע הצטרפות</div>
        {pStatus && (
          <span style={{ fontSize: 13, fontWeight: 600, color: STATUS_COLORS[pStatus] }}>
            {STATUS_LABELS[pStatus]}
          </span>
        )}
      </div>

      {/* Benefit selector */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8 }}>הטבה למצטרף חדש במבצע</div>

        {promoPackages && promoPackages.length > 0 && (
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 6 }}>בחר חבילה קיימת:</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
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
                      padding: '5px 10px', borderRadius: 8, fontSize: 12,
                      border: isMatch ? '1.5px solid var(--btn)' : '1px solid var(--border, rgba(255,255,255,0.15))',
                      background: isMatch ? 'var(--btn)' : 'var(--bg2)',
                      color: isMatch ? 'var(--btn-text)' : 'var(--text)',
                      cursor: 'pointer',
                    }}
                  >
                    {pkg.label}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 6 }}>או בחר הטבת מנהל:</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
          {[
            { label: '♾️ ללא הגבלה לצמיתות', searches: -2 },
            { label: '📅 מנוי חודשי (30 יום)', searches: -1 },
          ].map(opt => (
            <button
              key={opt.searches}
              onClick={() => { setPromoUnlimited(true); setPromoSearches(''); setPromoLabel(opt.label) }}
              style={{
                padding: '5px 10px', borderRadius: 8, fontSize: 12,
                border: (promoUnlimited && promoLabel === opt.label)
                  ? '1.5px solid var(--btn)' : '1px solid var(--border, rgba(255,255,255,0.15))',
                background: (promoUnlimited && promoLabel === opt.label) ? 'var(--btn)' : 'var(--bg2)',
                color: (promoUnlimited && promoLabel === opt.label) ? 'var(--btn-text)' : 'var(--text)',
                cursor: 'pointer',
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, fontSize: 14 }}>
          <input type="checkbox" checked={promoUnlimited} onChange={e => setPromoUnlimited(e.target.checked)} style={{ width: 16, height: 16 }} />
          ללא הגבלת כמות חיפושים
        </label>
        {!promoUnlimited && (
          <input className="input" type="number" min="0" placeholder="0 = בטל מבצע" value={promoSearches} onChange={e => setPromoSearches(e.target.value)} style={{ marginBottom: 8 }} />
        )}
      </div>

      <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14, fontSize: 14, cursor: 'pointer' }}>
        <input type="checkbox" checked={promoIsSubscriber} onChange={e => setPromoIsSubscriber(e.target.checked)} style={{ width: 16, height: 16 }} />
        <span>הוסף לקבוצת <b>מנויים</b> (מנוי פעיל)</span>
      </label>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 6 }}>תוקף ההטבה מיום ההצטרפות (ימים, 0 = ללא תפוגה)</div>
        <input className="input" type="number" min="0" placeholder="30" value={promoDurationDays} onChange={e => setPromoDurationDays(e.target.value)} style={{ marginBottom: 0 }} />
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 6 }}>תיאור ההטבה להודעת ברוכים הבאים</div>
        <input className="input" type="text" placeholder='לדוגמה: ♾️ מנוי חודשי ללא הגבלה' value={promoLabel} onChange={e => setPromoLabel(e.target.value)} style={{ marginBottom: 0 }} />
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 6 }}>תאריך תחילת המבצע</div>
        <input className="input" type="date" value={promoStart} onChange={e => setPromoStart(e.target.value)} style={{ marginBottom: 0 }} />
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 6 }}>תאריך סיום המבצע</div>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, fontSize: 14 }}>
          <input type="checkbox" checked={promoNoEnd} onChange={e => setPromoNoEnd(e.target.checked)} style={{ width: 16, height: 16 }} />
          ללא תאריך סיום
        </label>
        {!promoNoEnd && (
          <input className="input" type="date" value={promoEnd} onChange={e => setPromoEnd(e.target.value)} style={{ marginBottom: 0 }} />
        )}
      </div>

      <div style={{ background: 'var(--bg2)', borderRadius: 10, padding: '10px 12px', fontSize: 12, color: 'var(--hint)', marginBottom: 14, lineHeight: 1.5 }}>
        כל מי שיצטרף בתקופת המבצע יקבל את ההטבה שהוגדרה למעלה.
        תוקף ההטבה מתחיל ביום ההצטרפות של כל משתמש בנפרד.
        ביום האחרון של ההטבה המשתמש יקבל הודעת תזכורת.
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-success" style={{ flex: 1, marginTop: 0 }} disabled={saving} onClick={savePromo}>
          {saving ? '...' : '💾 שמור מבצע'}
        </button>
        {(settings.promo_searches ?? 0) !== 0 && (
          <button className="btn" style={{ flex: 1, marginTop: 0, background: 'var(--btn-danger, #e53e3e)', color: '#fff' }} disabled={saving} onClick={clearPromo}>
            🗑️ בטל מבצע
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
    <div>
      <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4 }}>⭐ פיצ'רים למנויים</div>
      <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 18 }}>
        הגדרות גישה לפיצ'רים המיועדים למנויים בלבד.
      </div>

      {/* Yad2 market price */}
      <div style={{ border: '1.5px solid var(--border, rgba(255,255,255,0.12))', borderRadius: 14, padding: 16 }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14 }}>💰 שווי שוק Yad2</div>

        <div className="toggle-row">
          <span className="toggle-label">הפעל הצגת שווי שוק</span>
          <button className={`toggle ${yad2Enabled ? 'on' : ''}`} onClick={() => setYad2Enabled(v => !v)} />
        </div>

        {yad2Enabled && (
          <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Public mode */}
            <div style={{ background: 'var(--bg2)', borderRadius: 10, padding: 12 }}>
              <div className="toggle-row" style={{ paddingTop: 0 }}>
                <span className="toggle-label" style={{ fontSize: 14 }}>🌐 פתוח לכולם</span>
                <button className={`toggle ${yad2Public ? 'on' : ''}`} onClick={() => setYad2Public(v => !v)} />
              </div>
              {yad2Public && (
                <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ fontSize: 12, color: 'var(--hint)' }}>טקסט תצוגה למשתמש</div>
                  <input type="text" className="input" style={{ marginBottom: 0 }}
                    placeholder='לדוגמה: פתוח לכולם עד 01/07/2026'
                    value={yad2PublicLabel} onChange={e => setYad2PublicLabel(e.target.value)} />
                  <div style={{ fontSize: 12, color: 'var(--hint)' }}>תאריך התחלה (אופציונלי)</div>
                  <input type="date" className="input" style={{ marginBottom: 0 }}
                    value={yad2PublicStart} onChange={e => setYad2PublicStart(e.target.value)} />
                  <div style={{ fontSize: 12, color: 'var(--hint)' }}>תאריך סיום (אופציונלי)</div>
                  <input type="date" className="input" style={{ marginBottom: 0 }}
                    value={yad2PublicEnd} onChange={e => setYad2PublicEnd(e.target.value)} />
                  {(() => {
                    const today = new Date().toISOString().slice(0, 10)
                    const inWindow = (!yad2PublicStart || today >= yad2PublicStart) &&
                                     (!yad2PublicEnd   || today <= yad2PublicEnd)
                    return (
                      <div style={{ fontSize: 12, fontWeight: 600, color: inWindow ? '#38a169' : '#d69e2e' }}>
                        {inWindow ? '🟢 פעיל כעת לכולם' : '🟡 לא פעיל (מחוץ לטווח התאריכים)'}
                      </div>
                    )
                  })()}
                </div>
              )}
            </div>

          </div>
        )}

        <button className="btn btn-success" style={{ marginTop: 14 }} disabled={yad2Saving} onClick={saveYad2}>
          {yad2Saving ? '...' : '💾 שמור'}
        </button>
      </div>

      {/* PDF report */}
      <div style={{ border: '1.5px solid var(--border, rgba(255,255,255,0.12))', borderRadius: 14, padding: 16, marginTop: 16 }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14 }}>📄 הורדת דוח PDF</div>

        <div className="toggle-row">
          <span className="toggle-label">הפעל הורדת PDF למנויים</span>
          <button className={`toggle ${pdfEnabled ? 'on' : ''}`} onClick={() => setPdfEnabled(v => !v)} />
        </div>

        {pdfEnabled && (
          <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Public mode */}
            <div style={{ background: 'var(--bg2)', borderRadius: 10, padding: 12 }}>
              <div className="toggle-row" style={{ paddingTop: 0 }}>
                <span className="toggle-label" style={{ fontSize: 14 }}>🌐 פתוח לכולם</span>
                <button className={`toggle ${pdfPublic ? 'on' : ''}`} onClick={() => setPdfPublic(v => !v)} />
              </div>
              {pdfPublic && (
                <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ fontSize: 12, color: 'var(--hint)' }}>טקסט תצוגה למשתמש</div>
                  <input type="text" className="input" style={{ marginBottom: 0 }}
                    placeholder='לדוגמה: פתוח לכולם עד 01/07/2026'
                    value={pdfPublicLabel} onChange={e => setPdfPublicLabel(e.target.value)} />
                  <div style={{ fontSize: 12, color: 'var(--hint)' }}>תאריך התחלה (אופציונלי)</div>
                  <input type="date" className="input" style={{ marginBottom: 0 }}
                    value={pdfPublicStart} onChange={e => setPdfPublicStart(e.target.value)} />
                  <div style={{ fontSize: 12, color: 'var(--hint)' }}>תאריך סיום (אופציונלי)</div>
                  <input type="date" className="input" style={{ marginBottom: 0 }}
                    value={pdfPublicEnd} onChange={e => setPdfPublicEnd(e.target.value)} />
                  {(() => {
                    const today = new Date().toISOString().slice(0, 10)
                    const inWindow = (!pdfPublicStart || today >= pdfPublicStart) &&
                                     (!pdfPublicEnd   || today <= pdfPublicEnd)
                    return (
                      <div style={{ fontSize: 12, fontWeight: 600, color: inWindow ? '#38a169' : '#d69e2e' }}>
                        {inWindow ? '🟢 פעיל כעת לכולם' : '🟡 לא פעיל (מחוץ לטווח התאריכים)'}
                      </div>
                    )
                  })()}
                </div>
              )}
            </div>

          </div>
        )}

        <button className="btn btn-success" style={{ marginTop: 14 }} disabled={pdfSaving} onClick={savePdf}>
          {pdfSaving ? '...' : '💾 שמור'}
        </button>
      </div>
    </div>
  )
}

function SettingsTab() {
  const [settings, setSettings]     = useState(null)
  const [saving, setSaving]         = useState(false)
  const [freeInput, setFreeInput]   = useState('')
  const [referralInput, setReferralInput] = useState('')

  useEffect(() => {
    adminFetchSettings().then(s => {
      setSettings(s)
      setFreeInput(String(s.free_searches ?? 10))
      setReferralInput(String(s.referral_bonus ?? 10))
    }).catch(() => {})
  }, [])

  async function toggleMaintenance() {
    setSaving(true)
    try {
      await adminUpdateSettings({ maintenance: !settings.maintenance })
      setSettings(s => ({ ...s, maintenance: !s.maintenance }))
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function saveFree() {
    setSaving(true)
    try {
      const v = parseInt(freeInput) || 0
      await adminUpdateSettings({ free_searches: v })
      setSettings(s => ({ ...s, free_searches: v }))
      window.Telegram?.WebApp?.showAlert('✅ עודכן')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function saveReferral() {
    setSaving(true)
    try {
      await adminUpdateSettings({ referral_bonus: parseInt(referralInput) })
      setSettings(s => ({ ...s, referral_bonus: parseInt(referralInput) }))
      window.Telegram?.WebApp?.showAlert('✅ עודכן')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  if (!settings) return <div className="loading"></div>

  return (
    <div>
      {/* Maintenance */}
      <div className="toggle-row">
        <span className="toggle-label">🔧 מצב תחזוקה</span>
        <button className={`toggle ${settings.maintenance ? 'on' : ''}`} onClick={toggleMaintenance} disabled={saving} />
      </div>

      {/* Free searches */}
      <div style={{ marginTop: 20 }}>
        <div className="toggle-label" style={{ marginBottom: 8 }}>🆓 חיפושים חינמיים למשתמש חדש</div>
        <input className="input" type="number" min="0" value={freeInput} onChange={e => setFreeInput(e.target.value)} />
        <button className="btn" disabled={saving} onClick={saveFree}>{saving ? '...' : 'שמור'}</button>
      </div>

      {/* Referral bonus */}
      <div style={{ marginTop: 20 }}>
        <div className="toggle-label" style={{ marginBottom: 8 }}>🤝 חיפושים לבונוס הפניה</div>
        <input className="input" type="number" min="1" value={referralInput} onChange={e => setReferralInput(e.target.value)} />
        <button className="btn" disabled={saving} onClick={saveReferral}>{saving ? '...' : 'שמור'}</button>
      </div>
    </div>
  )
}

function BroadcastTab() {
  const [msg, setMsg]             = useState('')
  const [imageb64, setImageb64]   = useState('')
  const [preview, setPreview]     = useState('')
  const [sending, setSending]     = useState(false)
  const [history, setHistory]     = useState(null)
  const [viewing, setViewing]     = useState(null)
  const fileRef                   = useRef()

  async function loadHistory() {
    try { setHistory(await adminFetchBroadcastHistory()) } catch { setHistory([]) }
  }

  useEffect(() => { loadHistory() }, [])

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
    window.Telegram?.WebApp?.showConfirm(
      `לשלוח הודעה לכל המשתמשים?\n\n"${msg.slice(0, 80)}"`,
      async ok => {
        if (!ok) return
        setSending(true)
        try {
          const res = await adminBroadcast(msg.trim(), imageb64)
          window.Telegram?.WebApp?.showAlert(`✅ נשלח ל-${res.sent} משתמשים${res.failed ? `, נכשל: ${res.failed}` : ''}`)
          setMsg(''); clearImage()
          await loadHistory()
        } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
        setSending(false)
      }
    )
  }

  function fmtDate(s) { return fmtDateTime(s) }

  return (
    <div>
      <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 14 }}>📢 שידור הודעה לכולם</div>

      {/* Message input */}
      <textarea
        className="input"
        rows={4}
        placeholder="כתוב הודעה לכל המשתמשים... (תומך Markdown)"
        value={msg}
        onChange={e => setMsg(e.target.value)}
        style={{ resize: 'vertical', fontFamily: 'inherit' }}
      />

      {/* Image picker */}
      <div style={{ marginTop: 8, marginBottom: 12 }}>
        {preview ? (
          <div style={{ position: 'relative', display: 'inline-block' }}>
            <img src={preview} alt="" style={{ maxWidth: '100%', maxHeight: 180, borderRadius: 10, display: 'block' }} />
            <button
              onClick={clearImage}
              style={{
                position: 'absolute', top: 6, right: 6,
                background: 'rgba(0,0,0,0.55)', color: '#fff',
                border: 'none', borderRadius: '50%', width: 26, height: 26,
                cursor: 'pointer', fontSize: 14, lineHeight: '26px', textAlign: 'center',
              }}
            >✕</button>
          </div>
        ) : (
          <button
            onClick={() => fileRef.current?.click()}
            style={{
              padding: '7px 14px', borderRadius: 8, fontSize: 13,
              border: '1.5px dashed var(--border, rgba(255,255,255,0.2))',
              background: 'var(--bg2)', color: 'var(--hint)', cursor: 'pointer',
            }}
          >
            🖼 הוסף תמונה (אופציונלי)
          </button>
        )}
        <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFile} />
      </div>

      <button className="btn" disabled={sending || !msg.trim()} onClick={send} style={{ marginBottom: 0 }}>
        {sending ? '⏳ שולח...' : '📢 שלח לכולם'}
      </button>

      {/* History */}
      <div style={{ marginTop: 28, fontWeight: 600, fontSize: 14, marginBottom: 10 }}>📋 היסטוריית שידורים</div>
      {history === null && <div className="loading"></div>}
      {history && history.length === 0 && (
        <div style={{ fontSize: 13, color: 'var(--hint)' }}>אין שידורים עדיין</div>
      )}
      {history && history.map(h => (
        <div
          key={h.id}
          onClick={() => setViewing(h)}
          style={{
            padding: '10px 12px', marginBottom: 8, borderRadius: 10,
            background: 'var(--bg2)', cursor: 'pointer',
            border: '1px solid var(--border, rgba(255,255,255,0.08))',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <div style={{ fontSize: 13, flex: 1, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis', color: 'var(--text)' }}>
              {h.has_image ? '🖼 ' : ''}{h.message}
            </div>
            <div style={{ fontSize: 11, color: 'var(--hint)', whiteSpace: 'nowrap' }}>{fmtDate(h.sent_at)}</div>
          </div>
          <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 4 }}>
            ✅ {h.sent}{h.failed ? ` · ❌ ${h.failed}` : ''}
          </div>
        </div>
      ))}

      {/* Viewer overlay */}
      {viewing && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={() => setViewing(null)}
        >
          <div
            style={{
              background: 'var(--bg)', borderRadius: '16px 16px 0 0',
              padding: 20, width: '100%', maxWidth: 480, maxHeight: '75vh',
              overflowY: 'auto',
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>📢 הודעת שידור</div>
            <div style={{ fontSize: 11, color: 'var(--hint)', marginBottom: 12 }}>
              {fmtDate(viewing.sent_at)} · ✅ {viewing.sent}{viewing.failed ? ` · ❌ ${viewing.failed}` : ''}
              {viewing.has_image ? ' · 🖼 כלל תמונה' : ''}
            </div>
            <div style={{
              background: 'var(--bg2)', borderRadius: 10, padding: '12px 14px',
              fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {viewing.message}
            </div>
            <button className="btn" style={{ marginTop: 14 }} onClick={() => setViewing(null)}>סגור</button>
          </div>
        </div>
      )}
    </div>
  )
}

const STATUS_LABEL = { open: 'פתוח', in_progress: 'בטיפול', closed: 'סגור' }
const STATUS_COLOR = { open: '#e07b00', in_progress: '#2481cc', closed: '#38a169' }

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
    <div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
        {[['open', 'פתוח'], ['in_progress', 'בטיפול'], ['closed', 'היסטוריה'], ['', 'הכל']].map(([val, label]) => (
          <button
            key={val}
            onClick={() => setFilter(val)}
            style={{
              padding: '5px 12px', fontSize: 12, borderRadius: 20, border: '1.5px solid var(--btn)',
              background: filter === val ? 'var(--btn)' : 'transparent',
              color: filter === val ? 'var(--btn-text)' : 'var(--btn)',
              cursor: 'pointer',
            }}
          >
            {label}{allTickets && counts[val] > 0 ? ` (${counts[val]})` : ''}
          </button>
        ))}
      </div>

      {!allTickets && <div className="loading"></div>}
      {visible && visible.length === 0 && (
        <div style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14, padding: 20 }}>אין פניות</div>
      )}
      {visible && visible.map(t => {
        const name = t.username ? `@${t.username}` : t.full_name || `id:${t.user_id}`
        return (
          <div key={t.id} className="card" style={{ cursor: 'pointer' }} onClick={() => setSelected(t.id)}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div className="card-title" style={{ fontSize: 14 }}>#{t.id} · {t.subject}</div>
                <div className="card-subtitle">{name} · {fmtDateIL(t.created_at)}</div>
              </div>
              <span style={{
                fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 10,
                background: STATUS_COLOR[t.status] + '22', color: STATUS_COLOR[t.status],
                whiteSpace: 'nowrap', marginRight: 8,
              }}>
                {STATUS_LABEL[t.status]}
              </span>
            </div>
          </div>
        )
      })}
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
    <div style={{ paddingBottom: 80 }}>
      <BackButton onClick={onBack} />
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontWeight: 700, fontSize: 15 }}>#{ticket.id} · {ticket.subject}</div>
        <div style={{ fontSize: 12, color: 'var(--hint)' }}>{name}</div>
      </div>

      <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        {[['open','🔴 פתוח'], ['in_progress','🟡 בטיפול'], ['closed','🟢 סגור']].map(([val, label]) => (
          <button
            key={val}
            disabled={updating || ticket.status === val}
            onClick={() => changeStatus(val)}
            style={{
              padding: '5px 12px', fontSize: 12, borderRadius: 20, border: '1.5px solid var(--btn)',
              background: ticket.status === val ? 'var(--btn)' : 'transparent',
              color: ticket.status === val ? 'var(--btn-text)' : 'var(--btn)',
              cursor: ticket.status === val ? 'default' : 'pointer',
              opacity: updating ? 0.6 : 1,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {allMessages.map((msg, i) => (
        <div key={msg.id || i} style={{
          display: 'flex', flexDirection: 'column',
          alignItems: msg.is_admin ? 'flex-end' : 'flex-start',
          marginBottom: 10,
        }}>
          <div style={{
            maxWidth: '85%',
            background: msg.is_admin ? 'var(--btn)' : 'var(--bg2)',
            color: msg.is_admin ? 'var(--btn-text)' : 'var(--text)',
            borderRadius: msg.is_admin ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
            padding: '10px 14px', fontSize: 14, lineHeight: 1.5, wordBreak: 'break-word',
          }}>
            {msg.message}
          </div>
          <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 3 }}>
            {msg.is_admin ? '🛠 תמיכה' : name} · {fmtDateTime(msg.created_at)}
          </div>
        </div>
      ))}

      {ticket.status !== 'closed' && (
        <div style={{ position: 'fixed', bottom: 0, right: 0, left: 0, padding: '10px 16px', background: 'var(--bg)', borderTop: '1px solid var(--bg2)', zIndex: 10 }}>
          <div style={{ display: 'flex', gap: 8, maxWidth: 480, margin: '0 auto' }}>
            <input
              className="input"
              style={{ flex: 1, marginBottom: 0 }}
              placeholder="תגובה למשתמש..."
              value={reply}
              onChange={e => setReply(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendReply()}
            />
            <button
              className="btn"
              style={{ width: 'auto', padding: '0 16px', marginTop: 0 }}
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

  async function deleteGroup(id, name) {
    window.Telegram?.WebApp?.showConfirm(`למחוק את הקבוצה "${name}"?`, async ok => {
      if (!ok) return
      try { await adminDeleteGroup(id); await loadGroups() }
      catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    })
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
    <div>
      {/* Create group */}
      <div style={{ background: 'var(--card-bg, rgba(255,255,255,0.05))', borderRadius: 12, padding: '12px 14px', marginBottom: 16 }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>➕ צור קבוצה</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            className="input"
            style={{ flex: 1, marginBottom: 0 }}
            placeholder="שם הקבוצה"
            value={newGroupName}
            onChange={e => setNewGroupName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && createGroup()}
          />
          <button
            className="btn"
            style={{ width: 'auto', padding: '0 16px', marginTop: 0 }}
            disabled={creating || !newGroupName.trim()}
            onClick={createGroup}
          >
            {creating ? '⏳' : 'צור'}
          </button>
        </div>
      </div>

      {/* Groups list */}
      {groups.length === 0 && (
        <div style={{ color: 'var(--hint)', textAlign: 'center', padding: 24 }}>אין קבוצות עדיין</div>
      )}
      {groups.map(group => (
        <div key={group.id} style={{ background: 'var(--card-bg, rgba(255,255,255,0.05))', borderRadius: 12, padding: '12px 14px', marginBottom: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15 }}>{group.name}</div>
              <div style={{ fontSize: 12, color: 'var(--hint)' }}>{group.member_ids.length} חברים</div>
            </div>
            <button
              className="btn btn-danger"
              style={{ width: 'auto', padding: '5px 12px', marginTop: 0, fontSize: 13 }}
              onClick={() => deleteGroup(group.id, group.name)}
            >
              🗑
            </button>
          </div>

          {/* Members */}
          {group.member_ids.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              {group.member_ids.map(uid => (
                <div key={uid} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid var(--bg)', fontSize: 13 }}>
                  <span>{getUserName(uid)}</span>
                  <button
                    onClick={() => removeMember(group.id, uid)}
                    style={{ background: 'none', border: 'none', color: '#e53e3e', cursor: 'pointer', fontSize: 16, padding: '0 4px' }}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add member */}
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <select
              className="input"
              style={{ flex: 1, marginBottom: 0 }}
              value={addingMember[group.id] || ''}
              onChange={e => setAddingMember(m => ({ ...m, [group.id]: e.target.value }))}
            >
              <option value="">הוסף משתמש...</option>
              {availableUsers(group).map(u => (
                <option key={u.user_id} value={u.user_id}>
                  {u.username ? `@${u.username}` : u.full_name || String(u.user_id)}
                </option>
              ))}
            </select>
            <button
              className="btn btn-success"
              style={{ width: 'auto', padding: '0 14px', marginTop: 0 }}
              disabled={!addingMember[group.id]}
              onClick={() => addMember(group.id)}
            >
              הוסף
            </button>
          </div>
        </div>
      ))}
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
      const results = await adminWatchPreview(make, model || '', year || null)
      setPreview(results)
    } catch (e) {
      setPreview([])
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
    <div>
      <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 12, lineHeight: 1.6 }}>
        הגדר מעקב אחרי מודעות ביד2. בכל 30 דקות המערכת בודקת אם נוספו מודעות חדשות ושולחת הודעה בטלגרם.
        מקסימום 5 התראות.
      </div>

      {watches.length === 0 && !adding && (
        <div style={{ color: 'var(--hint)', textAlign: 'center', padding: 24 }}>אין התראות פעילות עדיין</div>
      )}

      {watches.map(w => (
        <div key={w.id} style={{ marginBottom: 10 }}>
          <div className="card" style={{ opacity: w.active ? 1 : 0.55, transition: 'opacity 0.2s', marginBottom: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="card-title">
                  🔔 {w.make}{w.model ? ` ${w.model}` : ''}{w.year ? ` ${w.year}` : ''}
                </div>
                <div className="card-subtitle">
                  {w.active ? '🟢 פעיל' : '⏸ מושהה'} · {w.created_at?.slice(0, 10)}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 5, flexShrink: 0 }}>
                <button
                  className="btn"
                  style={{ width: 'auto', padding: '6px 10px', marginTop: 0, fontSize: 12, background: 'var(--bg)' }}
                  onClick={() => {
                    if (previewWatch === w.id) { setPreview(null); setPreviewWatch(null) }
                    else { setPreviewWatch(w.id); runPreview(w.make, w.model, w.year) }
                  }}
                  title="בדוק עכשיו"
                >🔍 בדוק</button>
                <button
                  className="btn"
                  style={{ width: 'auto', padding: '6px 10px', marginTop: 0, fontSize: 13 }}
                  onClick={() => toggleWatch(w.id)}
                  title={w.active ? 'השהה' : 'הפעל'}
                >{w.active ? '⏸' : '▶️'}</button>
                <button
                  className="btn btn-danger"
                  style={{ width: 'auto', padding: '6px 10px', marginTop: 0, fontSize: 13 }}
                  onClick={() => deleteWatch(w.id)}
                >🗑</button>
              </div>
            </div>
          </div>

          {/* Preview panel */}
          {previewWatch === w.id && (
            <div style={{
              background: 'var(--bg)', borderRadius: '0 0 12px 12px',
              borderTop: '1px solid rgba(255,255,255,0.08)',
              padding: '10px 14px',
            }}>
              {preview === 'loading' && (
                <div style={{ color: 'var(--hint)', fontSize: 13, textAlign: 'center', padding: '8px 0' }}>⏳ מחפש מודעות...</div>
              )}
              {Array.isArray(preview) && preview.length === 0 && (
                <div style={{ color: 'var(--hint)', fontSize: 13, textAlign: 'center', padding: '8px 0' }}>לא נמצאו מודעות תואמות</div>
              )}
              {Array.isArray(preview) && preview.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, color: 'var(--hint)', marginBottom: 8 }}>
                    {preview.length} מודעות נמצאו (מוצגות עד 5)
                  </div>
                  {preview.map((item, i) => (
                    <a key={i} href={item.link} target="_blank" rel="noreferrer" style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '8px 10px', background: 'var(--bg2)', borderRadius: 9,
                      marginBottom: 6, textDecoration: 'none', color: 'var(--text)',
                      gap: 8,
                    }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 700, fontSize: 13, color: '#38bdf8' }}>
                          {item.price ? `₪${Number(item.price).toLocaleString()}` : 'מחיר לא צוין'}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 2 }}>
                          {[
                            item.km ? `🛣️ ${Number(item.km).toLocaleString()} ק"מ` : null,
                            item.city ? `📍 ${item.city}` : null,
                            item.year ? `📅 ${item.year}` : null,
                          ].filter(Boolean).join('  ')}
                        </div>
                      </div>
                      <span style={{ fontSize: 16, color: 'var(--hint)', flexShrink: 0 }}>↗</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      {adding && (
        <div style={{ background: 'var(--bg2)', borderRadius: 14, padding: '14px 14px 10px', marginBottom: 10 }}>
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10 }}>➕ התראה חדשה</div>

          {/* Make dropdown */}
          <select
            className="input"
            value={form.make}
            onChange={e => setForm(f => ({ ...f, make: e.target.value, model: '', year: '' }))}
            style={{ marginBottom: 8 }}
          >
            <option value="">— בחר יצרן —</option>
            {makes.map(m => <option key={m} value={m}>{m}</option>)}
          </select>

          {/* Model dropdown — only shown when make is selected */}
          {form.make && (
            <select
              className="input"
              value={form.model}
              onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
              style={{ marginBottom: 8 }}
            >
              <option value="">— כל הדגמים —</option>
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          )}

          {/* Year dropdown */}
          <select
            className="input"
            value={form.year}
            onChange={e => setForm(f => ({ ...f, year: e.target.value }))}
            style={{ marginBottom: 10 }}
          >
            <option value="">— כל השנים —</option>
            {years.map(y => <option key={y} value={y}>{y}</option>)}
          </select>

          {/* Preview button */}
          {form.make && (
            <button
              type="button"
              className="btn btn-secondary"
              style={{ marginBottom: 10, marginTop: 0, fontSize: 13 }}
              onClick={() => runPreview(form.make, form.model, form.year ? parseInt(form.year) : null)}
            >🔍 בדוק עכשיו — ראה מודעות תואמות</button>
          )}

          {/* Inline preview for new watch form */}
          {preview === 'loading' && !previewWatch && (
            <div style={{ color: 'var(--hint)', fontSize: 13, marginBottom: 10 }}>⏳ מחפש...</div>
          )}
          {Array.isArray(preview) && !previewWatch && preview.length === 0 && (
            <div style={{ color: 'var(--hint)', fontSize: 12, marginBottom: 10 }}>לא נמצאו מודעות תואמות</div>
          )}
          {Array.isArray(preview) && !previewWatch && preview.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 11, color: 'var(--hint)', marginBottom: 6 }}>{preview.length} מודעות קיימות תואמות:</div>
              {preview.map((item, i) => (
                <a key={i} href={item.link} target="_blank" rel="noreferrer" style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '7px 10px', background: 'var(--bg)', borderRadius: 8,
                  marginBottom: 5, textDecoration: 'none', color: 'var(--text)', gap: 8,
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 700, fontSize: 13, color: '#38bdf8' }}>
                      {item.price ? `₪${Number(item.price).toLocaleString()}` : 'מחיר לא צוין'}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 2 }}>
                      {[
                        item.km ? `🛣️ ${Number(item.km).toLocaleString()} ק"מ` : null,
                        item.city ? `📍 ${item.city}` : null,
                      ].filter(Boolean).join('  ')}
                    </div>
                  </div>
                  <span style={{ fontSize: 15, color: 'var(--hint)' }}>↗</span>
                </a>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button
              className="btn"
              disabled={saving || !form.make}
              onClick={createWatch}
              style={{ flex: 1, marginTop: 0 }}
            >{saving ? '⏳...' : '✅ שמור'}</button>
            <button
              className="btn btn-secondary"
              onClick={() => { setAdding(false); setForm({ make: '', model: '', year: '' }); setPreview(null) }}
              style={{ flex: 1, marginTop: 0 }}
            >ביטול</button>
          </div>
        </div>
      )}

      {!adding && watches.length < 5 && (
        <button className="btn btn-success" style={{ marginTop: 6 }} onClick={() => { setAdding(true); setPreview(null); setPreviewWatch(null) }}>
          ➕ הוסף התראה
        </button>
      )}
    </div>
  )
}
