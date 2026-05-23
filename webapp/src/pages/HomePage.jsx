import { useState } from 'react'

const PLATE_RE = /^[\d\-]{5,10}$/

const menuItems = [
  { id: 'packages',  icon: '📦', label: 'חבילות',      sub: 'רכוש חיפושים' },
  { id: 'history',   icon: '📋', label: 'היסטוריה',    sub: 'חיפושים קודמים' },
  { id: 'referral',  icon: '🤝', label: 'הפנה חבר',    sub: 'קבל חיפושים בחינם' },
  { id: 'ticket',    icon: '🎫', label: 'תמיכה',        sub: 'פתח פנייה' },
  { id: 'howItWorks',icon: 'ℹ️', label: 'איך זה עובד', sub: 'מדריך שימוש' },
  { id: 'privacy',   icon: '🔒', label: 'פרטיות',       sub: 'תנאים ומדיניות' },
]

export default function HomePage({ user, onSearch, onNavigate }) {
  const [plate, setPlate] = useState('')
  const [error, setError]  = useState('')

  const searchesLeft = user?.searches_left
  const isUnlimited  = searchesLeft === -1

  function handleSearch() {
    const clean = plate.replace(/\s/g, '')
    if (!PLATE_RE.test(clean)) {
      setError('מספר לוחית לא תקין — הכנס 5–10 ספרות')
      return
    }
    setError('')
    onSearch(clean)
  }

  function handleKey(e) {
    if (e.key === 'Enter') handleSearch()
  }

  return (
    <div className="page" style={{ paddingBottom: 24 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <div style={{ fontSize: 40, lineHeight: 1 }}>🚗</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 18 }}>CarInfo Bot</div>
          {user ? (
            <div style={{ fontSize: 13, color: 'var(--hint)' }}>
              שלום {user.first_name} ·{' '}
              {isUnlimited
                ? <span style={{ color: '#7928ca', fontWeight: 600 }}>מנוי ♾️</span>
                : <><strong style={{ color: searchesLeft === 0 ? '#e53e3e' : 'var(--btn)' }}>{searchesLeft}</strong> חיפושים נותרו</>
              }
            </div>
          ) : (
            <div style={{ fontSize: 13, color: 'var(--hint)' }}>בדיקת רכבים מהירה</div>
          )}
        </div>
      </div>

      {/* Search box */}
      <div style={{
        background: 'var(--bg2)',
        borderRadius: 16,
        padding: 16,
        marginBottom: 20,
      }}>
        <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 10 }}>🔍 חיפוש רכב</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            className="input"
            style={{ marginBottom: 0, flex: 1, textAlign: 'center', letterSpacing: 2, fontSize: 18, fontWeight: 700 }}
            placeholder="12-345-67"
            value={plate}
            onChange={e => { setPlate(e.target.value); setError('') }}
            onKeyDown={handleKey}
            inputMode="numeric"
            maxLength={10}
          />
          <button
            onClick={handleSearch}
            style={{
              padding: '0 20px',
              border: 'none',
              borderRadius: 12,
              background: 'var(--btn)',
              color: 'var(--btn-text)',
              fontWeight: 700,
              fontSize: 15,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            חפש
          </button>
        </div>
        {error && (
          <div style={{ marginTop: 8, fontSize: 13, color: '#e53e3e' }}>{error}</div>
        )}
        {user && searchesLeft === 0 && (
          <div style={{ marginTop: 8, fontSize: 13, color: '#e53e3e' }}>
            אין לך חיפושים. <button
              onClick={() => onNavigate('packages')}
              style={{ background: 'none', border: 'none', color: 'var(--link)', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}
            >רכוש חבילה</button>
          </div>
        )}
      </div>

      {/* Referral banner */}
      <button
        onClick={() => onNavigate('referral')}
        style={{
          display: 'flex', alignItems: 'center', gap: 14, width: '100%',
          background: 'linear-gradient(135deg, #38a169 0%, #276749 100%)',
          border: 'none', borderRadius: 16, padding: '14px 18px',
          marginBottom: 20, cursor: 'pointer', textAlign: 'right',
        }}
      >
        <span style={{ fontSize: 34, flexShrink: 0 }}>🎁</span>
        <div>
          <div style={{ color: '#fff', fontWeight: 700, fontSize: 15, marginBottom: 2 }}>
            קבל חיפושים בחינם!
          </div>
          <div style={{ color: 'rgba(255,255,255,0.82)', fontSize: 12 }}>
            הפנה חברים וקבל חיפושים על כל הצטרפות ←
          </div>
        </div>
      </button>

      {/* Menu grid */}
      <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 10, fontWeight: 500 }}>
        תפריט ראשי
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 10,
      }}>
        {menuItems.map(item => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            style={{
              background: 'var(--bg2)',
              border: 'none',
              borderRadius: 14,
              padding: '16px 14px',
              textAlign: 'right',
              cursor: 'pointer',
              transition: 'opacity 0.15s',
            }}
          >
            <div style={{ fontSize: 28, marginBottom: 8 }}>{item.icon}</div>
            <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text)', marginBottom: 2 }}>
              {item.label}
            </div>
            <div style={{ fontSize: 12, color: 'var(--hint)' }}>{item.sub}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
