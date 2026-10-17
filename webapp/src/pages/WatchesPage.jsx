import { useState, useEffect } from 'react'
import { fetchUserWatches, deleteUserWatch, toggleUserWatch, createUserWatch, fetchWatchMakes, fetchWatchModels } from '../api.js'
import BackButton from '../components/BackButton.jsx'
import PageBanners from '../components/PageBanners.jsx'
import { SkeletonWatchCard } from '../components/SkeletonCard.jsx'

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 30 }, (_, i) => CURRENT_YEAR - i)

export default function WatchesPage({ onBack, onPackages, user, onNavigate }) {
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
    width: '100%', padding: '11px 13px', borderRadius: 13, fontSize: 14,
    background: '#fff', border: '1.5px solid var(--border-input)',
    color: 'var(--text-main)', marginBottom: 10, direction: 'rtl', fontFamily: 'inherit',
  }

  if (accessDenied) {
    return (
      <div className="page">
        {onBack && <BackButton onClick={() => onBack('home')} />}
        <div style={{ textAlign: 'center', padding: '32px 16px' }}>
          <div style={{ fontSize: 52, marginBottom: 16 }}>🔔</div>
          <h1 style={{ fontWeight: 700, fontSize: 20, marginBottom: 10 }}>התראות יד2</h1>
          <div style={{ fontSize: 14, color: 'var(--hint)', lineHeight: 1.6, marginBottom: 24 }}>
            קבל התראה בטלגרם ברגע שתתווסף מודעה חדשה ב-Yad2 לסוג הרכב שבחרת.
            <br />
            הפיצ׳ר זמין למנויים בלבד.
          </div>
          <div style={{
            background: 'rgba(255,255,255,0.85)', border: '1px solid var(--border)', borderRadius: 18, padding: '16px 20px',
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
                background: 'var(--grad-primary)',
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
      <h1 className="page-title" style={{ marginBottom: 4 }}>🔔 התראות יד2 שלי</h1>
      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 14 }}>
        תקבל הודעה בטלגרם כשתתווסף מודעה חדשה לסוג הרכב שבחרת.
      </div>

      <PageBanners page="watches" onNavigate={onNavigate} />

      {/* ── Usage bar ── */}
      {watches && user?.watch_max != null && (() => {
        const used = watches.length
        const max  = user.watch_max
        const pct  = max > 0 ? Math.min(100, Math.round((used / max) * 100)) : 0
        const full = used >= max
        return (
          <div className="card" style={{ padding: '12px 14px', marginBottom: 14 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>מעקבים פעילים</span>
              <span style={{
                fontSize: 13, fontWeight: 700,
                color: full ? 'var(--danger)' : used > 0 ? 'var(--primary)' : 'var(--text-muted)',
              }}>{used} / {max}</span>
            </div>
            <div aria-hidden="true" style={{ background: 'rgba(0, 100, 200, 0.1)', borderRadius: 20, height: 8, overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: 20,
                width: `${pct}%`,
                background: full ? 'var(--danger)' : 'linear-gradient(90deg, #0066d6, #00c6ff)',
                transition: 'width 0.4s ease',
              }} />
            </div>
            {full && (
              <div style={{ fontSize: 11, color: '#c53030', marginTop: 6 }}>
                הגעת למגבלה. מחק מעקב קיים או רכוש חבילת התראות נוספת.
              </div>
            )}
          </div>
        )
      })()}

      {error && <div role="alert" style={{ color: '#c53030', fontSize: 13, textAlign: 'center', padding: 16 }}>{error}</div>}
      {!watches && !error && (
        <div role="status" aria-label="טוען">
          <SkeletonWatchCard />
          <SkeletonWatchCard />
          <SkeletonWatchCard />
        </div>
      )}

      {/* ── Add form ── */}
      {watches && (
        adding ? (
          <div className="card" style={{ padding: 16, marginBottom: 14 }}>
            <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 12 }}>➕ הוסף מעקב חדש</div>

            <select aria-label="יצרן" value={selMake} onChange={e => setSelMake(e.target.value)} style={selectStyle}>
              <option value="">— בחר יצרן —</option>
              {makes.map(m => <option key={m} value={m}>{m}</option>)}
            </select>

            <select aria-label="דגם" value={selModel} onChange={e => setSelModel(e.target.value)} style={selectStyle} disabled={!selMake}>
              <option value="">— כל הדגמים —</option>
              {models.map(m => <option key={m} value={m}>{m}</option>)}
            </select>

            <select aria-label="שנה" value={selYear} onChange={e => setSelYear(e.target.value)} style={selectStyle}>
              <option value="">— כל השנים —</option>
              {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
            </select>

            {addError && <div role="alert" style={{ color: '#c53030', fontSize: 12, marginBottom: 8 }}>{addError}</div>}

            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={handleAdd}
                disabled={saving || !selMake}
                style={{
                  flex: 1, padding: '11px 0', borderRadius: 13, border: 'none',
                  background: (!selMake || saving) ? 'rgba(0,0,0,0.12)' : 'var(--grad-primary)',
                  color: (!selMake || saving) ? 'var(--hint)' : '#fff',
                  fontSize: 13, fontWeight: 600, cursor: (!selMake || saving) ? 'not-allowed' : 'pointer',
                }}
              >{saving ? '⏳...' : '🔔 הוסף מעקב'}</button>
              <button
                onClick={() => { setAdding(false); setAddError('') }}
                style={{
                  padding: '11px 16px', borderRadius: 13, border: '1px solid var(--border)',
                  background: '#fff', color: 'var(--text-muted)',
                  fontSize: 13, cursor: 'pointer',
                }}
              >ביטול</button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setAdding(true)}
            style={{
              width: '100%', padding: '12px 0', borderRadius: 14, border: '1.5px dashed rgba(0, 122, 255, 0.4)',
              background: 'rgba(0, 122, 255, 0.05)', color: 'var(--primary)',
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
              <div key={w.id} className="card" style={{
                margin: 0, padding: '14px 16px',
                border: w.active ? undefined : '1px dashed var(--text-muted)',
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
                      aria-label={`${w.active ? 'השהה' : 'הפעל'} מעקב: ${label}`}
                      style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 10, padding: '6px 10px', minWidth: 40, minHeight: 40, cursor: 'pointer', fontSize: 14 }}
                    ><span aria-hidden="true">{w.active ? '⏸️' : '▶️'}</span></button>
                    <button onClick={() => handleDelete(w.id)} title="מחק"
                      aria-label={`מחק מעקב: ${label}`}
                      style={{ background: 'rgba(255,59,48,0.1)', border: '1px solid rgba(255,59,48,0.25)', borderRadius: 10, padding: '6px 10px', minWidth: 40, minHeight: 40, cursor: 'pointer', fontSize: 14 }}
                    ><span aria-hidden="true">🗑️</span></button>
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
