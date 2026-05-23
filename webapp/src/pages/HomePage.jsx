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
  const searchesLeft = user?.searches_left
  const isUnlimited  = searchesLeft === -1
  const isSubscriber = !!user?.is_subscriber || isUnlimited
  const subLabel     = user?.subscription_label || null
  const quotaExpires = user?.quota_expires || null

  // Format expiry: "31/12/2025" or null
  function fmtExpiry(iso) {
    if (!iso) return null
    const d = new Date(iso)
    if (isNaN(d)) return null
    return `${String(d.getDate()).padStart(2,'0')}/${String(d.getMonth()+1).padStart(2,'0')}/${d.getFullYear()}`
  }

  // Status text for subscriber row
  function subStatusText() {
    if (!isSubscriber) return null
    if (isUnlimited && quotaExpires) return `בתוקף עד ${fmtExpiry(quotaExpires)}`
    if (isUnlimited && !quotaExpires) return 'לא מוגבל בזמן'
    return 'פעיל'
  }

  return (
    <div className="page" style={{ paddingBottom: 24 }}>

      {/* Status card */}
      {user && (
        <div style={{
          background: 'var(--bg2)', borderRadius: 14,
          padding: '14px 16px', marginBottom: 16,
          display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          {/* שם משתמש + תגית מנוי */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 13, color: 'var(--hint)' }}>שלום {user.first_name}</span>
            {isSubscriber
              ? <span style={{
                  background: 'linear-gradient(135deg,#1e40af,#0ea5e9)',
                  color: '#000', borderRadius: 20, padding: '3px 12px',
                  fontSize: 12, fontWeight: 500,
                }}>{subLabel || 'מנוי'}</span>
              : <span style={{
                  background: '#3a3a3a', color: '#aaa',
                  borderRadius: 20, padding: '3px 12px',
                  fontSize: 12, fontWeight: 500,
                }}>חינם</span>
            }
          </div>

          {/* סטטוס מנוי */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 13, color: 'var(--hint)' }}>סטטוס מנוי</span>
            {isSubscriber
              ? <span style={{ fontSize: 12, color: 'var(--text)', fontWeight: 500 }}>{subStatusText()}</span>
              : <span style={{ fontSize: 12, color: 'var(--hint)' }}>ללא מנוי</span>
            }
          </div>

          {/* יתרת חיפושים */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 13, color: 'var(--hint)' }}>יתרת חיפושים</span>
            <span style={{
              fontSize: 13, fontWeight: 700,
              color: isUnlimited ? '#38bdf8' : searchesLeft === 0 ? '#e53e3e' : 'var(--text)',
            }}>
              {isUnlimited ? '∞' : searchesLeft}
            </span>
          </div>

          {/* progress bar — רק אם יש מספר מוגבל */}
          {!isUnlimited && searchesLeft >= 0 && (() => {
            const total = user.searches_quota > 0 ? user.searches_quota : Math.max(searchesLeft, 10)
            const pct   = Math.min(100, Math.round((searchesLeft / total) * 100))
            const color = pct > 50 ? '#38a169' : pct > 20 ? '#d69e2e' : '#e53e3e'
            return (
              <div style={{ height: 6, background: 'var(--bg)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', width: `${pct}%`, background: color,
                  borderRadius: 4, transition: 'width 0.7s cubic-bezier(0.22,1,0.36,1)',
                }} />
              </div>
            )
          })()}
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

