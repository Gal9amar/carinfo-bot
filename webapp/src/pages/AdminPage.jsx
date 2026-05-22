import { useState, useEffect } from 'react'
import {
  adminFetchStats, adminFetchUsers, adminFetchSettings,
  adminUpdateSettings, adminFetchPackages,
  adminAddPackage, adminUpdatePackage, adminDeletePackage,
  adminGrantUser,
} from '../api.js'

const TABS = [
  { id: 'stats',    label: '📊 סטטיסטיקות' },
  { id: 'packages', label: '💰 חבילות' },
  { id: 'users',    label: '👥 משתמשים' },
  { id: 'settings', label: '⚙️ הגדרות' },
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
      {tab === 'packages' && <PackagesTab />}
      {tab === 'users'    && <UsersTab />}
      {tab === 'settings' && <SettingsTab />}
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

function PackagesTab() {
  const [pkgs, setPkgs] = useState(null)
  const [editing, setEditing] = useState(null)
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ label: '', searches: '', price: '' })
  const [saving, setSaving] = useState(false)

  useEffect(() => { adminFetchPackages().then(setPkgs).catch(() => {}) }, [])

  async function saveEdit() {
    setSaving(true)
    try {
      await adminUpdatePackage(editing.id, {
        label: form.label,
        searches: parseInt(form.searches),
        price: parseInt(form.price),
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

  const Modal = ({ title, onSave, onClose }) => (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">{title}</div>
        <input className="input" placeholder="שם החבילה" value={form.label} onChange={e => setForm(f => ({...f, label: e.target.value}))} />
        <input className="input" placeholder="חיפושים (-1 לבלתי מוגבל)" type="number" value={form.searches} onChange={e => setForm(f => ({...f, searches: e.target.value}))} />
        <input className="input" placeholder="מחיר (₪)" type="number" value={form.price} onChange={e => setForm(f => ({...f, price: e.target.value}))} />
        <button className="btn" disabled={saving} onClick={onSave}>{saving ? '...' : 'שמור'}</button>
        <button className="btn btn-secondary" style={{marginTop: 8}} onClick={onClose}>ביטול</button>
      </div>
    </div>
  )

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
                  onClick={() => { setEditing(pkg); setForm({ label: pkg.label, searches: String(pkg.searches), price: String(pkg.price) }) }}>
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
      <button className="btn btn-success" onClick={() => { setAdding(true); setForm({ label: '', searches: '', price: '' }) }}>
        ➕ הוסף חבילה
      </button>

      {editing && <Modal title="✏️ עריכת חבילה" onSave={saveEdit} onClose={() => setEditing(null)} />}
      {adding  && <Modal title="➕ חבילה חדשה"  onSave={saveAdd}  onClose={() => setAdding(false)} />}
    </div>
  )
}

function UsersTab() {
  const [users, setUsers] = useState(null)
  const [editingUser, setEditingUser] = useState(null)

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
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ color: 'var(--hint)', fontSize: 13 }}>{left} נותרו</span>
              <button
                className="btn"
                style={{ width: 'auto', padding: '4px 10px', marginTop: 0, fontSize: 12 }}
                onClick={() => setEditingUser(u)}
              >
                ✏️
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
    </div>
  )
}

function GrantModal({ user, onClose, onDone }) {
  const [packages, setPackages] = useState(null)
  const [mode, setMode] = useState('packages') // 'packages' | 'unlimited' | 'custom'
  const [unlimitedType, setUnlimitedType] = useState('permanent') // 'permanent' | 'monthly'
  const [customAmount, setCustomAmount] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => { adminFetchPackages().then(setPackages).catch(() => {}) }, [])

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

        <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
          {[['packages','📦 חבילה'],['unlimited','♾️ ללא הגבלה'],['custom','✍️ התאמה']].map(([id, label]) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              style={{
                flex: 1, padding: '7px 4px', fontSize: 12, borderRadius: 8,
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

        <button className="btn btn-secondary" style={{ marginTop: 8 }} onClick={onClose}>ביטול</button>
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
    </div>
  )
}
