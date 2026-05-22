import { useState } from 'react'
import { initiatePayment } from '../api.js'

export default function PackagesPage({ packages, user, onSelect, onPrivacy, onSupport, onHowItWorks, onHistory }) {
  const [loading, setLoading] = useState(null)

  async function handleSelect(pkg) {
    setLoading(pkg.id)
    try {
      const data = await initiatePayment(pkg.id)
      onSelect(pkg, data)
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה, נסה שוב.')
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="page">
      <div className="page-title">🛒 רכישת חבילת חיפושים</div>

      {user && (
        <div className="card" style={{ marginBottom: 16, background: 'var(--bg2)' }}>
          <span style={{ fontSize: 14, color: 'var(--hint)' }}>
            שלום {user.first_name} · נותרו לך{' '}
            <strong>{user.searches_left === -1 ? '∞' : user.searches_left}</strong> חיפושים
          </span>
        </div>
      )}

      {packages.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14 }}>
          אין חבילות זמינות כרגע
        </div>
      )}

      {packages.map(pkg => {
        const desc = pkg.searches === -1 ? 'ללא הגבלה' : `${pkg.searches} חיפושים`
        return (
          <div key={pkg.id} className="card">
            <div className="card-title">{pkg.label}</div>
            <div className="card-subtitle">{desc}</div>
            <div className="price-badge">₪{pkg.price}</div>
            <button
              className="btn"
              style={{ marginTop: 12 }}
              disabled={loading === pkg.id}
              onClick={() => handleSelect(pkg)}
            >
              {loading === pkg.id ? '...' : 'בחר חבילה'}
            </button>
          </div>
        )
      })}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 16 }}>
        <button className="btn btn-secondary" style={{ marginTop: 0 }} onClick={onHowItWorks}>
          ℹ️ איך זה עובד
        </button>
        <button className="btn btn-secondary" style={{ marginTop: 0 }} onClick={onHistory}>
          📜 היסטוריה
        </button>
      </div>

      <button
        className="btn btn-secondary"
        style={{ marginTop: 8 }}
        onClick={onSupport}
      >
        🎫 פניות ותמיכה
      </button>

      <div style={{ textAlign: 'center', marginTop: 16 }}>
        <button
          onClick={onPrivacy}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--hint)',
            fontSize: 12,
            cursor: 'pointer',
            textDecoration: 'underline',
          }}
        >
          מדיניות פרטיות
        </button>
      </div>
    </div>
  )
}
