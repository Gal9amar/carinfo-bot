import { useState, useEffect, useRef } from 'react'
import {
  adminFetchStats, adminFetchUsers, adminFetchSettings,
  adminUpdateSettings, adminFetchPackages,
  adminAddPackage, adminUpdatePackage, adminDeletePackage,
  adminGrantUser,
  adminRevokeSubscription,
  adminFetchTickets, adminFetchTicket, adminReplyTicket, adminUpdateTicketStatus,
  adminFetchPayments, adminApprovePayment, adminDeclinePayment,
  adminFetchCodes, adminCreateCode, adminDeleteCode,
  adminBroadcast,
  adminToggleBlock,
  adminSendUserMessage,
  adminFetchUserHistory,
  adminFetchUserReferrals,
  adminFetchActivity,
  adminGiftAll,
  adminFetchMarketPrice,
  adminFetchGroups,
  adminCreateGroup,
  adminDeleteGroup,
  adminAddGroupMember,
  adminRemoveGroupMember,
} from '../api.js'
import BackButton from '../components/BackButton.jsx'

const TABS = [
  { id: 'stats',    icon: '📊', label: 'סטטיסטיקות' },
  { id: 'activity', icon: '🕐', label: 'לוג פעילות' },
  { id: 'payments', icon: '💳', label: 'תשלומים' },
  { id: 'codes',    icon: '🔑', label: 'קודים' },
  { id: 'packages', icon: '⭐', label: 'מנויים' },
  { id: 'users',    icon: '👥', label: 'משתמשים' },
  { id: 'groups',   icon: '👥', label: 'קבוצות' },
  { id: 'settings', icon: '⚙️', label: 'הגדרות' },
  { id: 'tickets',  icon: '🎫', label: 'טיקטים' },
  { id: 'market',   icon: '💰', label: 'מחיר שוק' },
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
      {tab === 'codes'    && <CodesTab />}
      {tab === 'packages' && <PackagesTab />}
      {tab === 'users'    && <UsersTab />}
      {tab === 'groups'   && <GroupsTab />}
      {tab === 'settings' && <SettingsTab />}
      {tab === 'tickets'  && <TicketsTab />}
      {tab === 'market'   && <MarketPriceTab />}
    </div>
  )
}

function StatsTab() {
  const [stats, setStats] = useState(null)
  useEffect(() => { adminFetchStats().then(setStats).catch(() => {}) }, [])
  if (!stats) return <div className="loading">⏳</div>
  return (
    <div className="stat-grid">
      <div className="stat-card"><div className="stat-value">{stats.total_users}</div><div className="stat-label">משתמשים</div></div>
      <div className="stat-card"><div className="stat-value">{stats.active_users}</div><div className="stat-label">פעילים</div></div>
      <div className="stat-card"><div className="stat-value">{stats.total_searches}</div><div className="stat-label">בדיקות</div></div>
      <div className="stat-card"><div className="stat-value">{stats.used_codes}/{stats.total_codes}</div><div className="stat-label">קודים</div></div>
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

  function fmtTime(ts) {
    if (!ts) return ''
    try {
      const d = new Date(ts.replace(' ', 'T') + (ts.includes('+') ? '' : 'Z'))
      return d.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
             ' ' + d.toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit' })
    } catch { return ts.slice(0, 16) }
  }

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
      {!log && <div className="loading">⏳</div>}
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

function PackagesTab() {
  const [pkgs, setPkgs] = useState(null)
  const [editing, setEditing] = useState(null)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ label: '', searches: '', price: '', image_url: '' })
  const [saving, setSaving] = useState(false)

  useEffect(() => { adminFetchPackages().then(setPkgs).catch(() => {}) }, [])

  async function saveEdit() {
    setSaving(true)
    try {
      await adminUpdatePackage(editing.id, {
        label: form.label,
        searches: parseInt(form.searches),
        price: parseInt(form.price),
        image_url: form.image_url || '',
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

  if (!pkgs) return <div className="loading">⏳</div>

  return (
    <div>
      {pkgs.map(pkg => {
        const desc = pkg.searches === -1 ? 'ללא הגבלה' : `${pkg.searches} חיפושים`
        return (
          <div key={pkg.id} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div className="card-title">{pkg.label}</div>
                <div className="card-subtitle">{desc} · ₪{pkg.price}</div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn" style={{ width: 'auto', padding: '6px 12px', marginTop: 0, fontSize: 13 }}
                  onClick={() => { setEditing(pkg); setForm({ label: pkg.label, searches: String(pkg.searches), price: String(pkg.price), image_url: pkg.image_url || '' }) }}>
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
      <button className="btn btn-success" onClick={() => { setAdding(true); setForm({ label: '', searches: '', price: '', image_url: '' }) }}>
        ➕ הוסף מנוי
      </button>

      {editing && (
        <PackageModal
          title="✏️ עריכת מנוי"
          form={form} setForm={setForm}
          saving={saving} onSave={saveEdit} onClose={() => setEditing(null)}
        />
      )}
      {adding && (
        <PackageModal
          title="➕ מנוי חדש"
          form={form} setForm={setForm}
          saving={saving} onSave={saveAdd} onClose={() => setAdding(false)}
        />
      )}
    </div>
  )
}

function PackageModal({ title, form, setForm, saving, onSave, onClose }) {
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

        <button className="btn" disabled={saving} onClick={onSave}>{saving ? '...' : 'שמור'}</button>
        <button className="btn btn-secondary" style={{ marginTop: 8 }} onClick={onClose}>ביטול</button>
      </div>
    </div>
  )
}

function PaymentsTab() {
  const [payments, setPayments] = useState(null)
  const [acting, setActing] = useState(null) // ref being acted on

  function load() { adminFetchPayments().then(setPayments).catch(() => {}) }
  useEffect(() => { load() }, [])

  async function act(ref, action) {
    setActing(ref)
    try {
      if (action === 'approve') await adminApprovePayment(ref)
      else await adminDeclinePayment(ref)
      load()
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setActing(null)
  }

  if (!payments) return <div className="loading">⏳</div>

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)' }}>{payments.length} ממתינים</div>
        <button className="btn" style={{ width: 'auto', padding: '4px 12px', marginTop: 0, fontSize: 12 }} onClick={load}>🔄</button>
      </div>
      {payments.length === 0 && (
        <div style={{ color: 'var(--hint)', textAlign: 'center', padding: 24 }}>אין תשלומים ממתינים ✅</div>
      )}
      {payments.map(p => (
        <div key={p.ref} style={{ background: 'var(--card-bg, rgba(255,255,255,0.05))', borderRadius: 12, padding: '12px 14px', marginBottom: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontWeight: 700 }}>{p.label}</span>
            <span style={{ color: '#4caf50', fontWeight: 700 }}>₪{p.price}</span>
          </div>
          <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 8 }}>
            משתמש {p.user_id} · {p.created_at?.slice(0, 16).replace('T', ' ')}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className="btn btn-success"
              style={{ flex: 1, marginTop: 0, padding: '6px', fontSize: 13 }}
              disabled={acting === p.ref}
              onClick={() => act(p.ref, 'approve')}
            >
              ✅ אשר
            </button>
            <button
              className="btn btn-danger"
              style={{ flex: 1, marginTop: 0, padding: '6px', fontSize: 13 }}
              disabled={acting === p.ref}
              onClick={() => act(p.ref, 'decline')}
            >
              ❌ דחה
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

function CodesTab() {
  const [codes, setCodes] = useState(null)
  const [form, setForm] = useState({ searches: 50, unlimited: false, single_use: true, monthly: false })
  const [creating, setCreating] = useState(false)
  const [giftOpen, setGiftOpen] = useState(false)

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

  if (!codes) return <div className="loading">⏳</div>

  return (
    <div>
      {/* Gift all section */}
      <div style={{ background: 'var(--card-bg, rgba(255,255,255,0.05))', borderRadius: 12, padding: '12px 14px', marginBottom: 14 }}>
        <button
          onClick={() => setGiftOpen(o => !o)}
          style={{ width: '100%', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'right', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 0, color: 'var(--text)' }}
        >
          <span style={{ fontSize: 15, fontWeight: 700 }}>🎁 הענק מתנה לכל המשתמשים</span>
          <span style={{ fontSize: 12, color: 'var(--hint)' }}>{giftOpen ? '▲' : '▼'}</span>
        </button>
        {giftOpen && <GiftAllSection onDone={() => setGiftOpen(false)} />}
      </div>

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
    if (!searches || searches < 1) return
    const preview = `להוסיף ${searches} חיפושים לכל המשתמשים${message.trim() ? ' ולשלוח הודעה' : ''}?`
    window.Telegram?.WebApp?.showConfirm(preview, async ok => {
      if (!ok) return
      setSending(true)
      try {
        const res = await adminGiftAll(searches, message.trim(), imageb64)
        window.Telegram?.WebApp?.showAlert(
          `🎁 הושלם!\n✅ ${searches} חיפושים נוספו לכולם${res.notified ? `\n📤 הודעה נשלחה ל-${res.notified} משתמשים` : ''}`
        )
        setMessage('')
        setImageb64('')
        onDone()
      } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
      setSending(false)
    })
  }

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8 }}>כמות חיפושים לכל משתמש:</div>
      <input
        className="input"
        type="number"
        min="1"
        value={searches}
        onChange={e => setSearches(parseInt(e.target.value) || 1)}
        style={{ marginBottom: 10 }}
      />
      <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8 }}>הודעה למשתמשים (אופציונלי):</div>
      <textarea
        className="input"
        rows={3}
        placeholder="לדוגמה: 🎉 חגיגת שנה! קיבלת 10 חיפושים במתנה"
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
        disabled={sending || !searches || searches < 1}
        onClick={send}
        style={{ marginTop: 0, background: 'linear-gradient(135deg,#f5a623,#f76b1c)', border: 'none' }}
      >
        {sending ? '⏳ מעבד...' : `🎁 הענק ${searches || ''} חיפושים לכולם`}
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

function UsersTab() {
  const [users, setUsers]         = useState(null)
  const [filter, setFilter]       = useState('all') // all | free | subscriber | empty | blocked
  const [search, setSearch]       = useState('')
  const [editingUser, setEditingUser]   = useState(null)
  const [messagingUser, setMessagingUser] = useState(null)

  function load() { adminFetchUsers().then(setUsers).catch(() => {}) }
  useEffect(() => { load() }, [])
  if (!users) return <div className="loading">⏳</div>

  const filtered = users.filter(u => {
    const st = userStatus(u)
    if (filter === 'subscriber' && st.label !== 'מנוי') return false
    if (filter === 'free'       && st.label !== 'חינם') return false
    if (filter === 'empty'      && st.label !== 'אזל')  return false
    if (filter === 'blocked'    && st.label !== 'חסום') return false
    if (search) {
      const q = search.toLowerCase()
      const name = (u.username || u.full_name || '').toLowerCase()
      if (!name.includes(q) && !String(u.user_id).includes(q)) return false
    }
    return true
  })

  const FILTERS = [
    ['all', 'הכל'],
    ['subscriber', 'מנויים'],
    ['free', 'חינם'],
    ['empty', 'אזל'],
    ['blocked', 'חסום'],
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
      <div style={{ display: 'flex', gap: 4, marginBottom: 12, background: 'var(--bg)', borderRadius: 10, padding: 3 }}>
        {FILTERS.map(([id, label]) => {
          const count = id === 'all' ? users.length : users.filter(u => userStatus(u).label === (
            id === 'subscriber' ? 'מנוי' : id === 'free' ? 'חינם' : id === 'empty' ? 'אזל' : 'חסום'
          )).length
          return (
            <button key={id} onClick={() => setFilter(id)} style={{
              flex: 1, padding: '5px 2px', fontSize: 10, borderRadius: 7, border: 'none',
              background: filter === id ? 'var(--bg2)' : 'transparent',
              color: filter === id ? 'var(--text)' : 'var(--hint)',
              cursor: 'pointer', fontWeight: filter === id ? 600 : 400,
            }}>
              {label}<br/>
              <span style={{ fontSize: 11, opacity: 0.7 }}>{count}</span>
            </button>
          )
        })}
      </div>

      <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 8 }}>{filtered.length} משתמשים</div>

      {filtered.map(u => {
        const name = u.username ? `@${u.username}` : u.full_name || `id:${u.user_id}`
        const st   = userStatus(u)
        const left = u.searches_left === -1 ? '∞' : u.searches_left
        const expiry = u.quota_expires ? u.quota_expires.slice(0,10) : null
        return (
          <div key={u.user_id} style={{
            background: 'var(--bg2)', borderRadius: 12, padding: '10px 12px',
            marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8,
          }}>
            {/* Info */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{name}</span>
                <span style={{
                  fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 20,
                  background: st.bg, color: st.color, flexShrink: 0,
                }}>{st.label}</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--hint)' }}>
                {left} חיפושים נותרו
                {expiry && <span> · עד {expiry}</span>}
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 5, flexShrink: 0 }}>
              <button style={{ padding: '5px 9px', borderRadius: 8, border: 'none', background: 'var(--bg)', cursor: 'pointer', fontSize: 13 }}
                onClick={() => setEditingUser(u)}>✏️</button>
              <button style={{ padding: '5px 9px', borderRadius: 8, border: 'none', background: 'var(--bg)', cursor: 'pointer', fontSize: 13 }}
                onClick={() => setMessagingUser(u)}>💬</button>
              <button style={{ padding: '5px 9px', borderRadius: 8, border: 'none', background: u.blocked ? '#38a16922' : '#e53e3e22', cursor: 'pointer', fontSize: 13 }}
                onClick={async () => {
                  try { await adminToggleBlock(u.user_id); load() }
                  catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
                }}>{u.blocked ? '🔓' : '🚫'}</button>
            </div>
          </div>
        )
      })}

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
  const [packages, setPackages] = useState(null)
  const [mode, setMode] = useState('packages') // 'packages' | 'unlimited' | 'custom' | 'history' | 'referrals'
  const [unlimitedType, setUnlimitedType] = useState(null)
  const [customAmount, setCustomAmount] = useState('')
  const [saving, setSaving] = useState(false)
  const [history, setHistory] = useState(null)
  const [referralData, setReferralData] = useState(null)

  useEffect(() => { adminFetchPackages().then(setPackages).catch(() => {}) }, [])
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

  const TABS = [
    ['packages',  '⭐', 'מנוי'],
    ['unlimited', '♾️', 'ללא הגבלה'],
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

        {mode === 'packages' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {!packages && <div style={{ fontSize: 13, color: 'var(--hint)', textAlign: 'center', padding: 12 }}>⏳</div>}
            {packages && packages.map(pkg => (
              <button
                key={pkg.id}
                disabled={saving}
                onClick={() => grant(pkg.searches)}
                style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.08)',
                  background: 'var(--bg)', cursor: 'pointer', opacity: saving ? 0.5 : 1,
                }}
              >
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{pkg.label}</span>
                <span style={{ fontSize: 12, color: 'var(--hint)' }}>{pkg.searches === -1 ? '∞' : pkg.searches} חיפושים</span>
              </button>
            ))}

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

        {mode === 'unlimited' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[['permanent','♾️ ללא הגבלת זמן'],['monthly','📅 מנוי חודשי (30 יום)']].map(([val, label]) => (
              <label
                key={val}
                onClick={() => setUnlimitedType(prev => prev === val ? null : val)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px',
                  borderRadius: 10, cursor: 'pointer',
                  background: unlimitedType === val ? 'var(--accent)22' : 'var(--bg)',
                  border: `1px solid ${unlimitedType === val ? 'var(--accent)' : 'rgba(255,255,255,0.08)'}`,
                }}
              >
                <input type="radio" checked={unlimitedType === val} onChange={() => {}} style={{ accentColor: 'var(--accent)' }} />
                <span style={{ fontSize: 13 }}>{label}</span>
              </label>
            ))}
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <button
                disabled={saving || !unlimitedType}
                onClick={() => grant(unlimitedType === 'permanent' ? -2 : -1)}
                style={{
                  flex: 1, padding: '10px', borderRadius: 10, border: 'none',
                  background: 'var(--accent)', color: '#fff', fontSize: 13,
                  fontWeight: 600, cursor: unlimitedType ? 'pointer' : 'default',
                  opacity: (saving || !unlimitedType) ? 0.4 : 1,
                }}
              >{saving ? '...' : 'אשר'}</button>
              <button
                onClick={onClose}
                style={{
                  flex: 1, padding: '10px', borderRadius: 10,
                  border: '1px solid rgba(255,255,255,0.12)',
                  background: 'transparent', color: 'var(--hint)', fontSize: 13,
                  cursor: 'pointer',
                }}
              >ביטול</button>
            </div>
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
            {history === null && <div className="loading" style={{ fontSize: 13 }}>⏳ טוען...</div>}
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
            {referralData === null && <div className="loading" style={{ fontSize: 13 }}>⏳ טוען...</div>}
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

        <button className="btn btn-secondary" style={{ marginTop: 8 }} onClick={onClose}>ביטול</button>
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

function SettingsTab() {
  const [settings, setSettings]     = useState(null)
  const [saving, setSaving]         = useState(false)
  const [freeInput, setFreeInput]   = useState('')
  const [referralInput, setReferralInput] = useState('')

  // promo state
  const [promoSearches, setPromoSearches] = useState('0')
  const [promoUnlimited, setPromoUnlimited] = useState(false)
  const [promoNoEnd, setPromoNoEnd]         = useState(false)
  const [promoStart, setPromoStart]         = useState('')
  const [promoEnd, setPromoEnd]             = useState('')

  useEffect(() => {
    adminFetchSettings().then(s => {
      setSettings(s)
      setFreeInput(String(s.free_searches ?? 10))
      setReferralInput(String(s.referral_bonus ?? 10))
      const ps = s.promo_searches ?? 0
      setPromoUnlimited(ps === -1)
      setPromoSearches(ps === -1 ? '' : String(ps))
      setPromoStart(s.promo_start || '')
      setPromoEnd(s.promo_end || '')
      setPromoNoEnd(!s.promo_end)
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

  async function savePromo() {
    setSaving(true)
    try {
      const ps = promoUnlimited ? -1 : (parseInt(promoSearches) || 0)
      await adminUpdateSettings({
        promo_searches: ps,
        promo_start:    promoStart,
        promo_end:      promoNoEnd ? '' : promoEnd,
      })
      setSettings(s => ({ ...s, promo_searches: ps, promo_start: promoStart, promo_end: promoNoEnd ? '' : promoEnd }))
      window.Telegram?.WebApp?.showAlert('✅ מבצע עודכן')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  async function clearPromo() {
    setSaving(true)
    try {
      await adminUpdateSettings({ promo_searches: 0, promo_start: '', promo_end: '' })
      setSettings(s => ({ ...s, promo_searches: 0, promo_start: '', promo_end: '' }))
      setPromoSearches('0'); setPromoUnlimited(false); setPromoStart(''); setPromoEnd(''); setPromoNoEnd(false)
      window.Telegram?.WebApp?.showAlert('✅ המבצע בוטל')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  // Yad2 market price state
  const [yad2Enabled, setYad2Enabled]           = useState(false)
  const [yad2Groups, setYad2Groups]             = useState([])
  const [allGroups, setAllGroups]               = useState(null)
  const [yad2Public, setYad2Public]             = useState(false)
  const [yad2PublicStart, setYad2PublicStart]   = useState('')
  const [yad2PublicEnd, setYad2PublicEnd]       = useState('')
  const [yad2PublicLabel, setYad2PublicLabel]   = useState('')
  const [yad2Saving, setYad2Saving]             = useState(false)

  useEffect(() => {
    adminFetchGroups().then(setAllGroups).catch(() => setAllGroups([]))
  }, [])

  useEffect(() => {
    if (settings) {
      setYad2Enabled(!!settings.yad2_market_enabled)
      setYad2Groups(settings.yad2_market_groups || [])
      setYad2Public(!!settings.yad2_market_public)
      setYad2PublicStart(settings.yad2_market_public_start || '')
      setYad2PublicEnd(settings.yad2_market_public_end || '')
      setYad2PublicLabel(settings.yad2_market_public_label || '')
    }
  }, [settings])

  async function saveYad2() {
    setYad2Saving(true)
    try {
      await adminUpdateSettings({
        yad2_market_enabled:      yad2Enabled,
        yad2_market_groups:       yad2Groups,
        yad2_market_public:        yad2Public,
        yad2_market_public_start:  yad2PublicStart,
        yad2_market_public_end:    yad2PublicEnd,
        yad2_market_public_label:  yad2PublicLabel,
      })
      window.Telegram?.WebApp?.showAlert('✅ הגדרות Yad2 עודכנו')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setYad2Saving(false)
  }

  function toggleYad2Group(id) {
    setYad2Groups(prev => prev.includes(id) ? prev.filter(g => g !== id) : [...prev, id])
  }

  // Is the promo currently active?
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

  if (!settings) return <div className="loading">⏳</div>

  const STATUS_COLORS = { active: '#38a169', upcoming: '#d69e2e', expired: '#e53e3e' }
  const STATUS_LABELS = { active: '🟢 פעיל כעת', upcoming: '🟡 טרם התחיל', expired: '🔴 הסתיים' }
  const pStatus = promoStatus()

  return (
    <div>
      {/* Maintenance */}
      <div className="toggle-row">
        <span className="toggle-label">🔧 מצב תחזוקה</span>
        <button
          className={`toggle ${settings.maintenance ? 'on' : ''}`}
          onClick={toggleMaintenance}
          disabled={saving}
        />
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

      {/* Join promotion */}
      <div style={{ marginTop: 24, border: '1.5px solid var(--border, rgba(255,255,255,0.12))', borderRadius: 14, padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <div style={{ fontWeight: 700, fontSize: 15 }}>🎉 מבצע הצטרפות</div>
          {pStatus && (
            <span style={{ fontSize: 12, fontWeight: 600, color: STATUS_COLORS[pStatus] }}>
              {STATUS_LABELS[pStatus]}
            </span>
          )}
        </div>

        {/* Promo searches */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 6 }}>חיפושים שיקבל מצטרף חדש במבצע</div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, fontSize: 14 }}>
            <input
              type="checkbox"
              checked={promoUnlimited}
              onChange={e => setPromoUnlimited(e.target.checked)}
              style={{ width: 16, height: 16 }}
            />
            ללא הגבלה (גישה מלאה)
          </label>
          {!promoUnlimited && (
            <input
              className="input"
              type="number"
              min="0"
              placeholder="0 = בטל מבצע"
              value={promoSearches}
              onChange={e => setPromoSearches(e.target.value)}
              style={{ marginBottom: 0 }}
            />
          )}
        </div>

        {/* Date range */}
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 6 }}>תאריך תחילת המבצע</div>
          <input
            className="input"
            type="date"
            value={promoStart}
            onChange={e => setPromoStart(e.target.value)}
            style={{ marginBottom: 0 }}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 6 }}>תאריך סיום המבצע</div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, fontSize: 14 }}>
            <input
              type="checkbox"
              checked={promoNoEnd}
              onChange={e => setPromoNoEnd(e.target.checked)}
              style={{ width: 16, height: 16 }}
            />
            ללא תאריך סיום
          </label>
          {!promoNoEnd && (
            <input
              className="input"
              type="date"
              value={promoEnd}
              onChange={e => setPromoEnd(e.target.value)}
              style={{ marginBottom: 0 }}
            />
          )}
        </div>

        {/* Info note */}
        <div style={{ background: 'var(--bg2)', borderRadius: 10, padding: '10px 12px', fontSize: 12, color: 'var(--hint)', marginBottom: 14, lineHeight: 1.5 }}>
          כל מי שיצטרף בתקופת המבצע יקבל את כמות חיפושי המבצע במקום {settings.free_searches ?? 10} הרגילים.
          בסיום התקופה המערכת חוזרת אוטומטית לברירת המחדל.
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

      {/* Broadcast */}
      <div style={{ marginTop: 24 }}>
        <div className="toggle-label" style={{ marginBottom: 8 }}>📢 שידור הודעה לכל המשתמשים</div>
        <BroadcastSection />
      </div>

      {/* Yad2 market price feature flag */}
      <div style={{ marginTop: 24, border: '1.5px solid var(--border, rgba(255,255,255,0.12))', borderRadius: 14, padding: 16 }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14 }}>💰 מחיר שוק Yad2 — הצגה בדוח</div>

        <div className="toggle-row">
          <span className="toggle-label">הפעל הצגת מחיר שוק</span>
          <button
            className={`toggle ${yad2Enabled ? 'on' : ''}`}
            onClick={() => setYad2Enabled(v => !v)}
          />
        </div>

        {yad2Enabled && (
          <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Public mode */}
            <div style={{ background: 'var(--bg2)', borderRadius: 10, padding: 12 }}>
              <div className="toggle-row" style={{ paddingTop: 0 }}>
                <span className="toggle-label" style={{ fontSize: 14 }}>🌐 פתוח לכולם</span>
                <button
                  className={`toggle ${yad2Public ? 'on' : ''}`}
                  onClick={() => setYad2Public(v => !v)}
                />
              </div>
              {yad2Public && (
                <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ fontSize: 12, color: 'var(--hint)' }}>טקסט תצוגה למשתמש</div>
                  <input
                    type="text"
                    className="input"
                    style={{ marginBottom: 0 }}
                    placeholder='לדוגמה: פתוח לכולם עד 01/07/2026'
                    value={yad2PublicLabel}
                    onChange={e => setYad2PublicLabel(e.target.value)}
                  />
                  <div style={{ fontSize: 12, color: 'var(--hint)' }}>תאריך התחלה (אופציונלי)</div>
                  <input
                    type="date"
                    className="input"
                    style={{ marginBottom: 0 }}
                    value={yad2PublicStart}
                    onChange={e => setYad2PublicStart(e.target.value)}
                  />
                  <div style={{ fontSize: 12, color: 'var(--hint)' }}>תאריך סיום (אופציונלי)</div>
                  <input
                    type="date"
                    className="input"
                    style={{ marginBottom: 0 }}
                    value={yad2PublicEnd}
                    onChange={e => setYad2PublicEnd(e.target.value)}
                  />
                  {/* Status indicator */}
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

            {/* Groups mode */}
            <div>
              <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8 }}>
                הגבלה לקבוצות <span style={{ fontSize: 11 }}>(בנוסף למצב פתוח לכולם)</span>
              </div>
              {allGroups === null && <div style={{ fontSize: 13, color: 'var(--hint)' }}>⏳ טוען קבוצות...</div>}
              {allGroups && allGroups.length === 0 && (
                <div style={{ fontSize: 13, color: 'var(--hint)' }}>אין קבוצות — צור קבוצות בטאב קבוצות</div>
              )}
              {allGroups && allGroups.map(g => (
                <label key={g.id} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, fontSize: 14, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={yad2Groups.includes(g.id)}
                    onChange={() => toggleYad2Group(g.id)}
                    style={{ width: 16, height: 16 }}
                  />
                  {g.name} <span style={{ fontSize: 12, color: 'var(--hint)' }}>({g.member_ids.length} חברים)</span>
                </label>
              ))}
            </div>
          </div>
        )}

        <button
          className="btn btn-success"
          style={{ marginTop: 14 }}
          disabled={yad2Saving}
          onClick={saveYad2}
        >
          {yad2Saving ? '...' : '💾 שמור הגדרות Yad2'}
        </button>
      </div>
    </div>
  )
}

function BroadcastSection() {
  const [msg, setMsg] = useState('')
  const [sending, setSending] = useState(false)

  async function send() {
    if (!msg.trim()) return
    window.Telegram?.WebApp?.showConfirm(`לשלוח הודעה לכל המשתמשים?\n\n"${msg.slice(0, 80)}"`, async ok => {
      if (!ok) return
      setSending(true)
      try {
        const res = await adminBroadcast(msg.trim())
        window.Telegram?.WebApp?.showAlert(`✅ נשלח ל-${res.sent} משתמשים${res.failed ? `, נכשל: ${res.failed}` : ''}`)
        setMsg('')
      } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
      setSending(false)
    })
  }

  return (
    <div>
      <textarea
        className="input"
        rows={4}
        placeholder="כתוב הודעה לכל המשתמשים..."
        value={msg}
        onChange={e => setMsg(e.target.value)}
        style={{ resize: 'vertical' }}
      />
      <button className="btn" disabled={sending || !msg.trim()} onClick={send}>
        {sending ? '⏳ שולח...' : '📢 שלח לכולם'}
      </button>
    </div>
  )
}

const STATUS_LABEL = { open: 'פתוח', in_progress: 'בטיפול', closed: 'סגור' }
const STATUS_COLOR = { open: '#e07b00', in_progress: '#2481cc', closed: '#38a169' }

function TicketsTab() {
  const [tickets, setTickets] = useState(null)
  const [filter, setFilter] = useState('') // '' = all
  const [selected, setSelected] = useState(null)

  async function load() {
    const data = await adminFetchTickets(filter || undefined)
    setTickets(data)
  }

  useEffect(() => { load().catch(() => {}) }, [filter])

  if (selected) {
    return (
      <AdminTicketThread
        ticketId={selected}
        onBack={async () => { setSelected(null); await load() }}
      />
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
        {[['', 'הכל'], ['open', 'פתוח'], ['in_progress', 'בטיפול'], ['closed', 'סגור']].map(([val, label]) => (
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
            {label}
          </button>
        ))}
      </div>

      {!tickets && <div className="loading">⏳</div>}
      {tickets && tickets.length === 0 && (
        <div style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14, padding: 20 }}>אין פניות</div>
      )}
      {tickets && tickets.map(t => {
        const name = t.username ? `@${t.username}` : t.full_name || `id:${t.user_id}`
        return (
          <div key={t.id} className="card" style={{ cursor: 'pointer' }} onClick={() => setSelected(t.id)}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div className="card-title" style={{ fontSize: 14 }}>#{t.id} · {t.subject}</div>
                <div className="card-subtitle">{name} · {t.created_at?.slice(0, 10)}</div>
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

  if (!ticket) return <div className="loading">⏳</div>

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
            {msg.is_admin ? '🛠 תמיכה' : name} · {msg.created_at?.slice(0, 16).replace('T', ' ')}
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

// ── Market Price Tab ─────────────────────────────────────────────────────────
function MarketPriceTab() {
  const [plate, setPlate] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function search() {
    const clean = plate.replace(/[^0-9]/g, '')
    if (!clean) return
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const data = await adminFetchMarketPrice(clean)
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const m = result?.market

  // Filter listings by the vehicle's exact year (Yad2 API doesn't always filter server-side)
  const vehicleYear = result?.year ? parseInt(result.year) : null
  const filteredItems = vehicleYear && m?.items?.length
    ? m.items.filter(item => parseInt(item.vehicleDates?.yearOfProduction || 0) === vehicleYear)
    : m?.items || []
  const yearMismatch = vehicleYear && m?.items?.length > 0 && filteredItems.length === 0

  // Recompute stats from filtered items only
  const prices = filteredItems.map(i => i.price).filter(Boolean).sort((a, b) => a - b)
  const kms    = filteredItems.map(i => i.km).filter(Boolean)
  const stats  = prices.length > 0 ? {
    count:  prices.length,
    total:  m?.total,
    min:    prices[0],
    max:    prices[prices.length - 1],
    avg:    Math.round(prices.reduce((a, b) => a + b, 0) / prices.length),
    median: prices[Math.floor(prices.length / 2)],
    avg_km: kms.length > 0 ? Math.round(kms.reduce((a, b) => a + b, 0) / kms.length) : null,
  } : null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ fontSize: 13, color: 'var(--hint)', lineHeight: 1.5 }}>
        הזן לוחית רישוי — המערכת תשלוף פרטי רכב ותחפש מחיר שוק חי מ-Yad2 לפי יצרן / דגם / שנה.
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          type="tel"
          placeholder="מספר לוחית (ספרות בלבד)"
          value={plate}
          onChange={e => setPlate(e.target.value.replace(/[^0-9]/g, ''))}
          onKeyDown={e => e.key === 'Enter' && search()}
          maxLength={8}
          style={{
            flex: 1, padding: '10px 12px', borderRadius: 10, border: '1px solid var(--border)',
            background: 'var(--bg2)', color: 'var(--text)', fontSize: 16,
            textAlign: 'center', letterSpacing: 2,
          }}
        />
        <button
          className="btn"
          style={{ width: 'auto', padding: '0 18px' }}
          onClick={search}
          disabled={loading || !plate}
        >
          {loading ? '⏳' : '🔍 חפש'}
        </button>
      </div>

      {error && (
        <div style={{ background: '#ff3b3022', borderRadius: 10, padding: 12, color: '#ff3b30', fontSize: 13 }}>
          ❌ {error}
        </div>
      )}

      {result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ background: 'var(--bg2)', borderRadius: 12, padding: 14 }}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8 }}>🚗 פרטי הרכב</div>
            <MRow label="יצרן"   value={result.make} />
            <MRow label="דגם"    value={result.model} />
            <MRow label="שנה"    value={result.year} />
            <MRow label="צבע"    value={result.color} />
            <MRow label="לוחית" value={result.plate} />
          </div>

          {yearMismatch && (
            <div style={{ background: '#ff9f0a22', borderRadius: 10, padding: 12, fontSize: 13, color: '#b8730a' }}>
              ⚠️ Yad2 החזיר {m.items.length} מודעות אך אף אחת לא תואמת שנתון {vehicleYear}. לא ניתן להציג מחיר שוק מדויק.
              {result.yad2_url && (
                <a href={result.yad2_url} target="_blank" rel="noopener noreferrer" style={{ display: 'block', marginTop: 8, color: 'var(--btn)', fontWeight: 600, textDecoration: 'none' }}>
                  🔗 חפש ידנית ב-Yad2
                </a>
              )}
            </div>
          )}

          {stats ? (
            <div style={{ background: 'var(--bg2)', borderRadius: 12, padding: 14 }}>
              <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8 }}>💰 מחיר שוק – Yad2</div>
              <MRow label="ממוצע שוק"  value={`₪${stats.median?.toLocaleString()}`} bold />
              <MRow label="מינימום"    value={`₪${stats.min?.toLocaleString()}`} />
              <MRow label="מקסימום"    value={`₪${stats.max?.toLocaleString()}`} />
              <MRow label="ק״מ ממוצע" value={stats.avg_km ? `${stats.avg_km.toLocaleString()} ק״מ` : '—'} />
              {result.yad2_url && (
                <a href={result.yad2_url} target="_blank" rel="noopener noreferrer" style={{
                  display: 'block', marginTop: 12, padding: '9px 0',
                  background: 'var(--btn)', color: 'var(--btn-text)',
                  borderRadius: 10, textAlign: 'center', fontSize: 13,
                  fontWeight: 600, textDecoration: 'none',
                }}>🔗 פתח חיפוש ב-Yad2</a>
              )}
            </div>
          ) : (
            <div style={{ background: 'var(--bg2)', borderRadius: 12, padding: 14, color: 'var(--hint)', fontSize: 13 }}>
              ⚠️ לא נמצאו נתוני מחיר שוק ב-Yad2 לרכב זה.
              {result.yad2_url && (
                <a href={result.yad2_url} target="_blank" rel="noopener noreferrer" style={{
                  display: 'block', marginTop: 10, color: 'var(--btn)', textDecoration: 'none', fontWeight: 600,
                }}>🔗 חפש ידנית ב-Yad2</a>
              )}
            </div>
          )}

        </div>
      )}
    </div>
  )
}

function MRow({ label, value, bold }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 13 }}>
      <span style={{ color: 'var(--hint)' }}>{label}</span>
      <span style={{ fontWeight: bold ? 700 : 400 }}>{value ?? '—'}</span>
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

  if (!groups) return <div className="loading">⏳</div>

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
