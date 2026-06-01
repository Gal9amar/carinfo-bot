import { useState, useEffect } from 'react'
import { fetchUserWatches, deleteUserWatch, toggleUserWatch, createUserWatch, fetchWatchMakes, fetchWatchModels } from '../api.js'
import BackButton from '../components/BackButton.jsx'

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 30 }, (_, i) => CURRENT_YEAR - i)

export default function WatchesPage({ onBack, onPackages, user }) {
  const [watches, setWatches]   = useState(null)
  const [error, setError]       = useState(null)
  const [accessDenied, setAccessDenied] = useState(false)
  const [adding, setAdding]     = useState(false)

  // Add form state
  const [makes, setMakes]       = useState([])
  const [models, setModels]     = useState([])
  const [selMake, setSelMake]   = useState('')
  const [selModel, setSelModel] = useState('')
  const [selYear, setSelYear]   = useState('')
  const [saving, setSaving]     = useState(false)
  const [addError, setAddError] = useState('')

  async function load() {
    try {
      const data = await fetchUserWatches()
      setWatches(data)
    } catch (e) {
      if (e.message === 'FORBIDDEN') setAccessDenied(true)
      else setError('שגיאה בטעינת המעקבים')
    }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (adding && makes.length === 0) {
      fetchWatchMakes().then(setMakes).catch(() => {})
    }
  }, [adding])

  useEffect(() => {
    setSelModel('')
    setModels([])
    if (selMake) {
      fetchWatchModels(selMake).then(setModels).catch(() => {})
    }
  }, [selMake])

  async function handleAdd() {
    if (!selMake) { setAddError('יש לבחור יצרן'); return }
    setSaving(true)
    setAddError('')
    try {
      await createUserWatch({ make: selMake, model: selModel, year: selYear ? parseInt(selYear) : null })
      await load()
      setAdding(false)
      setSelMake(''); setSelModel(''); setSelYear('')
    } catch (e) {
      setAddError(e.message || 'שגיאה בהוספת המעקב')
    }
    setSaving(false)
  }

  async function handleDelete(id) {
    window.Telegram?.WebApp?.showConfirm('למחוק את המעקב?', async (ok) => {
      if (!ok) return
      try {
        await deleteUserWatch(id)
        setWatches(prev => prev.filter(w => w.id !== id))
      } catch {
        window.Telegram?.WebApp?.showAlert('שגיאה במחיקה')
      }
    })
  }

  async function handleToggle(id) {
    try {
      await toggleUserWatch(id)
      setWatches(prev => prev.map(w => w.id === id ? { ...w, active: !w.active } : w))
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה')
    }
  }

  const selectStyle = {
    width: '100%', padding: '10px 12px', borderRadius: 10, fontSize: 14,
    background: 'var(--bg)', border: '1px solid rgba(255,255,255,0.12)',
    color: 'var(--text)', marginBottom: 10, direction: 'rtl',
  }

  if (accessDenied) {
    return (
      <div className="page">
        {onBack && <BackButton onClick={() => onBack('home')} />}
        <div style={{ textAlign: 'center', padding: '32px 16px' }}>
          <div style={{ fontSize: 52, marginBottom: 16 }}>🔔</div>
          <div style={{ fontWeight: 700, fontSize: 20, marginBottom: 10 }}>התראות יד2</div>
          <div style={{ fontSize: 14, color: 'var(--hint)', lineHeight: 1.6, marginBottom: 24 }}>
            קבל התראה בטלגרם ברגע שתתווסף מודעה חדשה ב-Yad2 לסוג הרכב שבחרת.
            <br />
            הפיצ׳ר זמין למנויים בלבד.
          </div>
          <div style={{
            background: 'var(--bg2)', borderRadius: 16, padding: '16px 20px',
            marginBottom: 24, textAlign: 'right', fontSize: 13, lineHeight: 1.8,
          }}>
            <div>✅ בחירת יצרן, דגם ושנה</div>
            <div>✅ עד מספר מעקבים במקביל</div>
            <div>✅ הודעה ישירה לטלגרם על כל מודעה חדשה</div>
          </div>
          {onPackages && (
            <button
              onClick={onPackages}
              style={{
                width: '100%', padding: '14px 0', borderRadius: 14, border: 'none',
                background: 'linear-gradient(135deg,#7c3aed,#a855f7)',
                color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer',
              }}
            >🛒 רכישת חבילה</button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      {onBack && <BackButton onClick={() => onBack('home')} />}
      <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 4 }}>🔔 התראות יד2 שלי</div>
      <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 12 }}>
        תקבל הודעה בטלגרם כשתתווסף מודעה חדשה לסוג הרכב שבחרת.
      </div>

      {/* ── Usage bar ── */}
      {watches && user?.watch_max != null && (() => {
        const used = watches.length
        const max  = user.watch_max
        const pct  = max > 0 ? Math.min(100, Math.round((used / max) * 100)) : 0
        const full = used >= max
        return (
          <div style={{ background: 'var(--bg2)', borderRadius: 12, padding: '12px 14px', marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>מעקבים פעילים</span>
              <span style={{
                fontSize: 13, fontWeight: 700,
                color: full ? '#e53e3e' : used > 0 ? '#a78bfa' : 'var(--hint)',
              }}>{used} / {max}</span>
            </div>
            <div style={{ background: 'var(--bg)', borderRadius: 20, height: 8, overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: 20,
                width: `${pct}%`,
                background: full ? '#e53e3e' : 'linear-gradient(90deg,#7c3aed,#a78bfa)',
                transition: 'width 0.4s ease',
              }} />
            </div>
            {full && (
              <div style={{ fontSize: 11, color: '#e53e3e', marginTop: 6 }}>
                הגעת למגבלה. מחק מעקב קיים או רכוש חבילת התראות נוספת.
              </div>
            )}
          </div>
        )
      })()}

      {error && <div style={{ color: '#e53e3e', fontSize: 13, textAlign: 'center', padding: 16 }}>{error}</div>}
      {!watches && !error && <div className="loading"></div>}

      {/* ── Add form ── */}
      {watches && (
        adding ? (
          <div style={{ background: 'var(--bg2)', borderRadius: 14, padding: 16, marginBottom: 16 }}>
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12 }}>➕ הוסף מעקב חדש</div>

            <select value={selMake} onChange={e => setSelMake(e.target.value)} style={selectStyle}>
              <option value="">— בחר יצרן —</option>
              {makes.map(m => <option key={m} value={m}>{m}</option>)}
            </select>

            <select value={selModel} onChange={e => setSelModel(e.target.value)} style={selectStyle} disabled={!selMake}>
              <option value="">— כל הדגמים —</option>
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>

            <select value={selYear} onChange={e => setSelYear(e.target.value)} style={selectStyle}>
              <option value="">— כל השנים —</option>
              {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
            </select>

            {addError && <div style={{ color: '#e53e3e', fontSize: 12, marginBottom: 8 }}>{addError}</div>}

            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={handleAdd}
                disabled={saving || !selMake}
                style={{
                  flex: 1, padding: '10px 0', borderRadius: 10, border: 'none',
                  background: (!selMake || saving) ? '#55555544' : '#8b5cf6',
                  color: (!selMake || saving) ? 'var(--hint)' : '#fff',
                  fontSize: 13, fontWeight: 600, cursor: (!selMake || saving) ? 'not-allowed' : 'pointer',
                }}
              >{saving ? '⏳...' : '🔔 הוסף מעקב'}</button>
              <button
                onClick={() => { setAdding(false); setAddError('') }}
                style={{
                  padding: '10px 16px', borderRadius: 10, border: 'none',
                  background: 'var(--bg)', color: 'var(--hint)',
                  fontSize: 13, cursor: 'pointer',
                }}
              >ביטול</button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setAdding(true)}
            style={{
              width: '100%', padding: '12px 0', borderRadius: 12, border: '1.5px dashed #8b5cf666',
              background: '#8b5cf611', color: '#a78bfa',
              fontSize: 14, fontWeight: 600, cursor: 'pointer', marginBottom: 16,
            }}
          >➕ הוסף מעקב חדש</button>
        )
      )}

      {/* ── Watch list ── */}
      {watches && watches.length === 0 && !adding && (
        <div style={{ textAlign: 'center', padding: '24px 16px', color: 'var(--hint)', fontSize: 14 }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🔔</div>
          <div>אין מעקבים פעילים.</div>
          <div style={{ fontSize: 12, marginTop: 6 }}>הוסף מעקב בכפתור למעלה או מתוך דוח רכב.</div>
        </div>
      )}

      {watches && watches.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {watches.map(w => {
            const label = [w.make, w.model, w.year].filter(Boolean).join(' ')
            return (
              <div key={w.id} style={{
                background: 'var(--bg2)', borderRadius: 14, padding: '14px 16px',
                borderRight: `3px solid ${w.active ? '#8b5cf6' : '#55555566'}`,
                opacity: w.active ? 1 : 0.6,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 15 }}>{label}</div>
                    <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 3 }}>
                      {w.active ? '🟢 פעיל' : '⏸️ מושהה'} · נוסף {w.created_at?.slice(0, 10)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button onClick={() => handleToggle(w.id)} title={w.active ? 'השהה' : 'הפעל'}
                      style={{ background: 'var(--bg)', border: 'none', borderRadius: 8, padding: '6px 10px', cursor: 'pointer', fontSize: 14 }}
                    >{w.active ? '⏸️' : '▶️'}</button>
                    <button onClick={() => handleDelete(w.id)} title="מחק"
                      style={{ background: '#e53e3e22', border: 'none', borderRadius: 8, padding: '6px 10px', cursor: 'pointer', fontSize: 14 }}
                    >🗑️</button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
