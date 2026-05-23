import { } from 'react'

const menuItems = [
  { id: 'packages',   icon: '⭐', label: 'רכישת מנוי',  sub: 'חיפושים + תכונות מנוי' },
  { id: 'history',    icon: '📋', label: 'היסטוריה',    sub: 'חיפושים קודמים' },
  { id: 'referral',   icon: '🤝', label: 'הפנה חבר',    sub: 'קבל חיפושים בחינם' },
  { id: 'ticket',     icon: '🎫', label: 'תמיכה',        sub: 'פתח פנייה' },
  { id: 'howItWorks', icon: 'ℹ️', label: 'איך זה עובד', sub: 'מדריך שימוש' },
  { id: 'privacy',    icon: '🔒', label: 'פרטיות',       sub: 'תנאים ומדיניות' },
]

const adminMenuItem = { id: 'admin', icon: '🛠', label: 'פאנל מנהל', sub: 'ניהול מערכת' }

export default function HomePage({ user, onNavigate }) {
  const searchesLeft   = user?.searches_left
  const isUnlimited    = searchesLeft === -1
  const isSubscriber   = !!user?.is_subscriber || isUnlimited

  return (
    <div className="page" style={{ paddingBottom: 24 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: isSubscriber ? 12 : 20 }}>
        <div style={{ fontSize: 40, lineHeight: 1 }}>🚗</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 18 }}>CarInfo Bot</div>
          {user ? (
            <div style={{ fontSize: 13, color: 'var(--hint)' }}>
              שלום {user.first_name} ·{' '}
              <strong style={{ color: searchesLeft === 0 ? '#e53e3e' : 'var(--btn)' }}>
                {isUnlimited ? '∞' : searchesLeft}
              </strong> חיפושים נותרו
            </div>
          ) : (
            <div style={{ fontSize: 13, color: 'var(--hint)' }}>בדיקת רכבים מהירה</div>
          )}
        </div>
        {isSubscriber && (
          <div style={{
            background: 'linear-gradient(135deg,#1e40af,#0ea5e9)',
            color: '#000', borderRadius: 20, padding: '5px 12px',
            fontSize: 12, fontWeight: 400, flexShrink: 0,
            boxShadow: '0 2px 8px #0ea5e944',
          }}>{user?.subscription_label || 'מנוי'}</div>
        )}
      </div>

      {/* Subscriber banner */}
      {isSubscriber && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12,
          background: 'linear-gradient(135deg,#7928ca22,#5a1e9911)',
          border: '1px solid #7928ca44',
          borderRadius: 14, padding: '12px 16px', marginBottom: 16,
        }}>
          <span style={{ fontSize: 26, flexShrink: 0 }}>⭐</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: '#a855f7' }}>חשבון מנוי פעיל</div>
            <div style={{ fontSize: 12, color: 'var(--hint)', marginTop: 2 }}>
              גישה לתכונות מנוי כולל מחיר שוק Yad2 בדוח הרכב
            </div>
          </div>
        </div>
      )}

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

      {/* Search progress bar */}
      {user && user.searches_left !== -1 && user.searches_left >= 0 && (
        (() => {
          const left = user.searches_left
          const total = user.searches_quota > 0 ? user.searches_quota : Math.max(left, 10)
          const pct = Math.min(100, Math.round((left / total) * 100))
          const color = pct > 50 ? '#38a169' : pct > 20 ? '#d69e2e' : '#e53e3e'
          return (
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--hint)', marginBottom: 5 }}>
                <span>חיפושים נותרים</span>
                <span style={{ fontWeight: 600, color }}>{left}</span>
              </div>
              <div style={{ height: 7, background: 'var(--bg2)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${pct}%`,
                  background: color,
                  borderRadius: 4,
                  transition: 'width 0.7s cubic-bezier(0.22,1,0.36,1)',
                }} />
              </div>
            </div>
          )
        })()
      )}

      {/* Menu grid */}
      <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 10, fontWeight: 500 }}>
        תפריט ראשי
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {[...menuItems, ...(user?.is_admin ? [adminMenuItem] : [])].map(item => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            style={{
              background: item.id === 'admin' ? 'linear-gradient(135deg,#2d3748,#1a202c)' : 'var(--bg2)',
              border: item.id === 'admin' ? '1px solid #4a5568' : 'none',
              borderRadius: 14,
              padding: '16px 14px',
              textAlign: 'right',
              cursor: 'pointer',
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

