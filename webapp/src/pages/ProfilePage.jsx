import { useState, useEffect } from 'react'
import { fetchUserOrders, fetchGarage, fetchReferral } from '../api.js'
import { fmtDate, fmtDateLong } from '../utils/time.js'
import BackButton from '../components/BackButton.jsx'

function initials(firstName, lastName) {
  const a = (firstName || '').trim().slice(0, 1)
  const b = (lastName  || '').trim().slice(0, 1)
  return (a + b).toUpperCase() || '👤'
}

export default function ProfilePage({ user, onNavigate, onBack }) {
  const [orders, setOrders]     = useState(null)
  const [garage, setGarage]     = useState(null)
  const [referral, setReferral] = useState(null)

  useEffect(() => {
    fetchUserOrders().catch(() => null).then(setOrders)
    fetchGarage().catch(() => null).then(setGarage)
    fetchReferral().catch(() => null).then(setReferral)
  }, [])

  if (!user) return <div className="loading"></div>

  const searchesLeft = user.searches_left
  const isUnlimited  = searchesLeft === -1
  const isSubscriber = !!user.is_subscriber || isUnlimited
  const subLabel     = user.subscription_label || (isSubscriber ? 'מנוי' : 'חינמי')
  const quotaExpires = user.quota_expires || null
  const fullName     = [user.first_name, user.last_name].filter(Boolean).join(' ') || 'משתמש'

  const ownedCount  = garage?.filter(g => g.status === 'owned').length ?? null
  const ordersCount = orders?.length ?? null

  const tiles = [
    { id: 'orders',   icon: '📦', label: 'היסטוריית הזמנות',   value: ordersCount },
    { id: 'history',  icon: '📋', label: 'היסטוריית חיפושים' },
    { id: 'garage',   icon: '🚘', label: 'רכבים שקניתי',       value: ownedCount },
    { id: 'watches',  icon: '🔔', label: 'ההתראות שלי' },
    { id: 'referral', icon: '🤝', label: 'הפנה חבר',           value: referral?.count },
    { id: 'packages', icon: '🛒', label: 'רכישת מוצר' },
    { id: 'ticket',   icon: '🎫', label: 'תמיכה' },
    ...(user.is_admin ? [{ id: 'admin', icon: '🛠', label: 'פאנל ניהול' }] : []),
  ]

  return (
    <div className="page" style={{ paddingBottom: 24 }}>
      <BackButton onClick={onBack} />
      <div className="page-title">👤 אזור אישי</div>

      {/* Identity header */}
      <div style={{
        background: 'linear-gradient(135deg, #1e40af 0%, #0ea5e9 100%)',
        borderRadius: 18,
        padding: '20px 18px',
        marginBottom: 14,
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        color: '#fff',
        boxShadow: '0 8px 24px rgba(14,165,233,0.25)',
      }}>
        <div style={{
          width: 56, height: 56, borderRadius: '50%', flexShrink: 0,
          background: 'rgba(255,255,255,0.18)',
          border: '2px solid rgba(255,255,255,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20, fontWeight: 800,
        }}>{initials(user.first_name, user.last_name)}</div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{
            fontSize: 18, fontWeight: 800,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{fullName}</div>
          {user.username && (
            <div style={{ fontSize: 13, opacity: 0.85 }}>@{user.username}</div>
          )}
          {user.first_seen && (
            <div style={{ fontSize: 12, opacity: 0.8, marginTop: 4 }}>
              🗓 הצטרף/ה ב-{fmtDateLong(user.first_seen)}
            </div>
          )}
        </div>
      </div>

      {/* Current plan */}
      <div style={{
        background: 'var(--bg2)', borderRadius: 14, padding: '14px 16px',
        marginBottom: 14, display: 'flex', flexDirection: 'column', gap: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 13, color: 'var(--hint)' }}>המסלול הנוכחי</span>
          <span style={{
            background: isSubscriber ? 'linear-gradient(135deg,#1e40af,#0ea5e9)' : '#3a3a3a',
            color: isSubscriber ? '#000' : '#aaa',
            borderRadius: 20, padding: '3px 12px', fontSize: 12, fontWeight: 600,
          }}>{subLabel}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 13, color: 'var(--hint)' }}>יתרת חיפושים</span>
          <span style={{
            fontSize: 14, fontWeight: 700,
            color: isUnlimited ? '#38bdf8' : searchesLeft === 0 ? '#e53e3e' : 'var(--text)',
          }}>{isUnlimited ? '∞' : searchesLeft}</span>
        </div>

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

        {isUnlimited && quotaExpires && (
          <div style={{ fontSize: 12, color: 'var(--hint)' }}>בתוקף עד {fmtDate(quotaExpires)}</div>
        )}

        {!isSubscriber && (
          <button className="btn" style={{ marginTop: 2 }} onClick={() => onNavigate('packages')}>
            🚀 שדרג עכשיו
          </button>
        )}
      </div>

      {/* Navigation grid */}
      <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 10, fontWeight: 500 }}>
        האזור שלי
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {tiles.map(t => (
          <button
            key={t.id}
            onClick={() => onNavigate(t.id)}
            style={{
              background: t.id === 'admin' ? 'linear-gradient(135deg,#2d3748,#1a202c)' : 'var(--bg2)',
              border: t.id === 'admin' ? '1px solid #4a5568' : 'none',
              borderRadius: 14,
              padding: '16px 14px',
              textAlign: 'right',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 26 }}>{t.icon}</span>
              {t.value != null && (
                <span style={{
                  fontSize: 12, fontWeight: 700, color: 'var(--btn)',
                  background: 'var(--bg)', borderRadius: 20, padding: '2px 8px',
                }}>{t.value}</span>
              )}
            </div>
            <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text)' }}>{t.label}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
