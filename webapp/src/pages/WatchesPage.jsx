import { useState, useEffect } from 'react'
import { fetchUserWatches, deleteUserWatch, toggleUserWatch } from '../api.js'
import BackButton from '../components/BackButton.jsx'

export default function WatchesPage({ onBack }) {
  const [watches, setWatches] = useState(null)
  const [error, setError] = useState(null)

  async function load() {
    try {
      const data = await fetchUserWatches()
      setWatches(data)
    } catch {
      setError('שגיאה בטעינת המעקבים')
    }
  }

  useEffect(() => { load() }, [])

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

  return (
    <div className="page">
      {onBack && <BackButton onClick={() => onBack('home')} />}
      <div style={{ fontWeight: 700, fontSize: 18, marginBottom: 4 }}>🔔 התראות יד2 שלי</div>
      <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 18 }}>
        תקבל הודעה בטלגרם כשתתווסף מודעה חדשה לסוג הרכב שבחרת.
      </div>

      {error && (
        <div style={{ color: '#e53e3e', fontSize: 13, textAlign: 'center', padding: 16 }}>{error}</div>
      )}

      {!watches && !error && <div className="loading"></div>}

      {watches && watches.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '32px 16px',
          color: 'var(--hint)', fontSize: 14,
        }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>🔔</div>
          <div>אין מעקבים פעילים.</div>
          <div style={{ fontSize: 12, marginTop: 6 }}>
            חפש רכב בבוט והוסף מעקב מתוך הדוח.
          </div>
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
                    <button
                      onClick={() => handleToggle(w.id)}
                      title={w.active ? 'השהה' : 'הפעל'}
                      style={{
                        background: 'var(--bg)', border: 'none', borderRadius: 8,
                        padding: '6px 10px', cursor: 'pointer', fontSize: 14,
                      }}
                    >{w.active ? '⏸️' : '▶️'}</button>
                    <button
                      onClick={() => handleDelete(w.id)}
                      title="מחק"
                      style={{
                        background: '#e53e3e22', border: 'none', borderRadius: 8,
                        padding: '6px 10px', cursor: 'pointer', fontSize: 14,
                      }}
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
