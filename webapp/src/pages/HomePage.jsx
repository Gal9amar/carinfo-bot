import { useState } from 'react'
import { fmtDate } from '../utils/time.js'
import PageBanners from '../components/PageBanners.jsx'

const menuItems = [
  { id: 'packages',   icon: '📦', label: 'חבילות ומנויים', sub: 'חיפושים מוזלים והתראות' },
  { id: 'history',    icon: '📄', label: 'הדוחות שלי',    sub: 'חיפושי עבר' },
  { id: 'orders',     icon: '💳', label: 'הזמנות שלי',   sub: 'היסטוריית רכישות' },
  { id: 'referral',   icon: '🎁', label: 'קבל קרדיט בחינם', sub: 'הפנה חברים' },
  { id: 'ticket',     icon: '💬', label: 'תמיכה',          sub: 'פניות וקשר' },
  { id: 'privacy',    icon: '🔒', label: 'פרטיות',         sub: 'מדיניות שימוש' },
]

export default function HomePage({ user, onNavigate, onSearchPlate }) {
  const [plateInput, setPlateInput] = useState('')

  const searchesLeft = user?.searches_left
  const isUnlimited  = searchesLeft === -1
  
  function handleSearch() {
    if (plateInput.length >= 5) {
      onSearchPlate(plateInput.trim())
    }
  }

  return (
    <div className="page" style={{ paddingBottom: 24 }}>
      <header style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginBottom: 24 }}>
        <div style={{ fontSize: 28, fontWeight: 900, letterSpacing: '-0.5px' }}>
          CarInfo<span style={{ color: 'var(--primary)' }}>.ai</span>
        </div>
      </header>

      <div className="card" style={{ padding: 24 }}>
        <h2 style={{ marginBottom: 8, fontWeight: 700, fontSize: 24 }}>בדיקת רכב</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: 15, marginBottom: 24, lineHeight: 1.5 }}>
          הקלד מספר רישוי לקבלת דוח היסטוריה, בעלות ושעבודים מקיף בתוך שניות.
        </p>
        
        <div className="input-group">
          <input 
            type="tel" 
            className="plate-input" 
            placeholder="מספר רישוי" 
            maxLength="8"
            value={plateInput}
            onChange={(e) => setPlateInput(e.target.value)}
          />
        </div>

        <button 
          className="btn btn-primary" 
          onClick={handleSearch}
          disabled={plateInput.length < 5}
        >
          חפש רכב
        </button>
      </div>

      {user && (
        <div className="card" style={{ display: 'flex', gap: 16, alignItems: 'center', cursor: 'pointer' }} onClick={() => onNavigate('packages')}>
          <div style={{ background: 'rgba(52, 199, 89, 0.1)', color: 'var(--secondary)', padding: 12, borderRadius: 16, fontSize: 24 }}>
            🎁
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, marginBottom: 4, fontSize: 16 }}>
              {isUnlimited ? 'מנוי ללא הגבלה' : `${searchesLeft} בדיקות נותרו`}
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              {isUnlimited ? 'בדיקות רכב חופשיות' : 'שתף עם חברים או רכוש חבילה'}
            </div>
          </div>
        </div>
      )}

      <PageBanners page="home" onNavigate={onNavigate} />

      <h3 style={{ fontSize: 18, fontWeight: 700, margin: '24px 0 16px', paddingRight: 8 }}>
        אפשרויות
      </h3>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {menuItems.map(item => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className="card"
            style={{
              padding: '16px 20px', margin: 0,
              display: 'flex', alignItems: 'center', gap: 16,
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 20, cursor: 'pointer', textAlign: 'right',
              boxShadow: '0 2px 10px rgba(0,0,0,0.02)'
            }}
          >
            <div style={{ fontSize: 28 }}>{item.icon}</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--text-main)', marginBottom: 2 }}>
                {item.label}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>{item.sub}</div>
            </div>
            <div style={{ color: 'var(--text-muted)' }}>←</div>
          </button>
        ))}
      </div>
    </div>
  )
}
