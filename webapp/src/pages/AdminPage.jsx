import { useState, useEffect, useRef } from 'react'
import {
  adminFetchStats, adminFetchUsers, adminFetchSettings,
  adminUpdateSettings, adminFetchPackages,
  adminAddPackage, adminUpdatePackage, adminDeletePackage,
  adminGrantUser,
  adminFetchTickets, adminFetchTicket, adminReplyTicket, adminUpdateTicketStatus,
  adminFetchPayments, adminApprovePayment, adminDeclinePayment,
  adminFetchCodes, adminCreateCode, adminDeleteCode,
  adminBroadcast,
  adminToggleBlock,
  adminSendUserMessage,
  adminFetchUserHistory,
  adminFetchActivity,
  adminGiftAll,
} from '../api.js'

const TABS = [
  { id: 'stats',    label: '📊 סטטיסטיקות' },
  { id: 'activity', label: '🕐 לוג' },
  { id: 'payments', label: '💳 תשלומים' },
  { id: 'codes',    label: '🔑 קודים' },
  { id: 'packages', label: '📦 חבילות' },
  { id: 'users',    label: '👥 משתמשים' },
  { id: 'settings', label: '⚙️ הגדרות' },
  { id: 'tickets',  label: '🎫 טיקטים' },
]

export default function AdminPage({ user }) {
  const [tab, setTab] = useState('stats')

  return (
    <div className="page">
      <div className="page-title">🛠 פאנל ניהול</div>
      <div className="tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'stats'    && <StatsTab />}
      {tab === 'activity' && <ActivityTab />}
      {tab === 'payments' && <PaymentsTab />}
      {tab === 'codes'    && <CodesTab />}
      {tab === 'packages' && <PackagesTab />}
      {tab === 'users'    && <UsersTab />}
      {tab === 'settings' && <SettingsTab />}
      {tab === 'tickets'  && <TicketsTab />}
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
    window.Telegram?.WebApp?.showConfirm('למחוק חבילה?', async (ok) => {
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
        ➕ הוסף חבילה
      </button>

      {editing && (
        <PackageModal
          title="✏️ עריכת חבילה"
          form={form} setForm={setForm}
          saving={saving} onSave={saveEdit} onClose={() => setEditing(null)}
        />
      )}
      {adding && (
        <PackageModal
          title="➕ חבילה חדשה"
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
          placeholder="שם החבילה"
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

function UsersTab() {
  const [users, setUsers] = useState(null)
  const [editingUser, setEditingUser] = useState(null)
  const [messagingUser, setMessagingUser] = useState(null)

  useEffect(() => { adminFetchUsers().then(setUsers).catch(() => {}) }, [])
  if (!users) return <div className="loading">⏳</div>

  return (
    <div>
      <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8 }}>{users.length} משתמשים</div>
      {users.slice(0, 50).map(u => {
        const name = u.username ? `@${u.username}` : u.full_name || `id:${u.user_id}`
        const left = u.searches_left === -1 ? '∞' : u.searches_left
        return (
          <div key={u.user_id} className="user-row">
            <span>{u.blocked ? '🔴' : '🟢'} {name}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ color: 'var(--hint)', fontSize: 13 }}>{left} נותרו</span>
              <button
                className="btn"
                style={{ width: 'auto', padding: '4px 10px', marginTop: 0, fontSize: 12 }}
                onClick={() => setEditingUser(u)}
              >
                ✏️
              </button>
              <button
                className="btn"
                style={{ width: 'auto', padding: '4px 10px', marginTop: 0, fontSize: 12 }}
                onClick={() => setMessagingUser(u)}
              >
                💬
              </button>
              <button
                className={`btn ${u.blocked ? 'btn-success' : 'btn-danger'}`}
                style={{ width: 'auto', padding: '4px 10px', marginTop: 0, fontSize: 12 }}
                onClick={async () => {
                  try {
                    await adminToggleBlock(u.user_id)
                    const fresh = await adminFetchUsers()
                    setUsers(fresh)
                  } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
                }}
              >
                {u.blocked ? '🔓' : '🚫'}
              </button>
            </div>
          </div>
        )
      })}
      {editingUser && (
        <GrantModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onDone={async () => {
            const fresh = await adminFetchUsers()
            setUsers(fresh)
            setEditingUser(null)
          }}
        />
      )}
      {messagingUser && (
        <SendMessageModal
          user={messagingUser}
          onClose={() => setMessagingUser(null)}
        />
      )}
    </div>
  )
}

function GrantModal({ user, onClose, onDone }) {
  const [packages, setPackages] = useState(null)
  const [mode, setMode] = useState('packages') // 'packages' | 'unlimited' | 'custom' | 'history'
  const [unlimitedType, setUnlimitedType] = useState('permanent') // 'permanent' | 'monthly'
  const [customAmount, setCustomAmount] = useState('')
  const [saving, setSaving] = useState(false)
  const [history, setHistory] = useState(null)

  useEffect(() => { adminFetchPackages().then(setPackages).catch(() => {}) }, [])
  useEffect(() => {
    if (mode === 'history' && history === null) {
      adminFetchUserHistory(user.user_id).then(setHistory).catch(() => setHistory([]))
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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">✏️ עריכת {name}</div>

        <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
          {[['packages','📦 חבילה'],['unlimited','♾️ ללא הגבלה'],['custom','✍️ התאמה'],['history','📋 היסטוריה']].map(([id, label]) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              style={{
                flex: 1, minWidth: '40%', padding: '7px 4px', fontSize: 12, borderRadius: 8,
                border: '1.5px solid var(--accent)',
                background: mode === id ? 'var(--accent)' : 'transparent',
                color: mode === id ? '#fff' : 'var(--accent)',
                cursor: 'pointer',
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {mode === 'packages' && (
          <div>
            {!packages && <div className="loading" style={{ fontSize: 13 }}>⏳</div>}
            {packages && packages.map(pkg => (
              <button
                key={pkg.id}
                className="btn"
                disabled={saving}
                style={{ marginBottom: 8, textAlign: 'right' }}
                onClick={() => grant(pkg.searches)}
              >
                {pkg.label} — {pkg.searches === -1 ? '∞' : pkg.searches} חיפושים
              </button>
            ))}
          </div>
        )}

        {mode === 'unlimited' && (
          <div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
              {[['permanent','♾️ ללא הגבלת זמן'],['monthly','📅 מנוי חודשי (30 יום)']].map(([val, label]) => (
                <label key={val} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input type="radio" checked={unlimitedType === val} onChange={() => setUnlimitedType(val)} />
                  {label}
                </label>
              ))}
            </div>
            <button className="btn" disabled={saving} onClick={() => grant(unlimitedType === 'permanent' ? -2 : -1)}>
              {saving ? '...' : 'אשר'}
            </button>
          </div>
        )}

        {mode === 'custom' && (
          <div>
            <input
              className="input"
              type="number"
              min="1"
              placeholder="כמות חיפושים להוסיף"
              value={customAmount}
              onChange={e => setCustomAmount(e.target.value)}
            />
            <button
              className="btn"
              disabled={saving || !customAmount || parseInt(customAmount) < 1}
              onClick={() => grant(parseInt(customAmount))}
            >
              {saving ? '...' : 'הוסף'}
            </button>
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
  const [settings, setSettings] = useState(null)
  const [saving, setSaving] = useState(false)
  const [freeInput, setFreeInput] = useState('')

  useEffect(() => {
    adminFetchSettings().then(s => {
      setSettings(s)
      setFreeInput(String(s.free_searches))
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
      await adminUpdateSettings({ free_searches: parseInt(freeInput) })
      setSettings(s => ({ ...s, free_searches: parseInt(freeInput) }))
      window.Telegram?.WebApp?.showAlert('✅ עודכן')
    } catch { window.Telegram?.WebApp?.showAlert('שגיאה') }
    setSaving(false)
  }

  if (!settings) return <div className="loading">⏳</div>

  return (
    <div>
      <div className="toggle-row">
        <span className="toggle-label">🔧 מצב תחזוקה</span>
        <button
          className={`toggle ${settings.maintenance ? 'on' : ''}`}
          onClick={toggleMaintenance}
          disabled={saving}
        />
      </div>
      <div style={{ marginTop: 20 }}>
        <div className="toggle-label" style={{ marginBottom: 8 }}>🆓 חיפושים חינמיים למשתמש חדש</div>
        <input
          className="input"
          type="number"
          value={freeInput}
          onChange={e => setFreeInput(e.target.value)}
        />
        <button className="btn" disabled={saving} onClick={saveFree}>
          {saving ? '...' : 'שמור'}
        </button>
      </div>
      <div style={{ marginTop: 24 }}>
        <div className="toggle-label" style={{ marginBottom: 8 }}>📢 שידור הודעה לכל המשתמשים</div>
        <BroadcastSection />
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
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--btn)', padding: '0 4px' }}>›</button>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 15 }}>#{ticket.id} · {ticket.subject}</div>
          <div style={{ fontSize: 12, color: 'var(--hint)' }}>{name}</div>
        </div>
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
