import { useState, useEffect } from 'react'
import { fetchUserOrders, fetchGarage, fetchReferral, fetchSearchHistory, fetchUserWatches, fetchPackages } from '../api.js'
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
  const [historyCount, setHistoryCount] = useState(null)
  const [watchesCount, setWatchesCount] = useState(null)
  const [packagesCount, setPackagesCount] = useState(null)

  useEffect(() => {
    fetchUserOrders().catch(() => null).then(setOrders)
    fetchGarage().catch(() => null).then(setGarage)
    fetchReferral().catch(() => null).then(setReferral)
    fetchSearchHistory().then(res => setHistoryCount(res?.length)).catch(() => null)
    fetchUserWatches().then(res => setWatchesCount(res?.length)).catch(() => null)
    fetchPackages().then(res => setPackagesCount(res?.length)).catch(() => null)
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
    { id: 'history',  icon: '📋', label: 'היסטוריית חיפושים', value: historyCount },
    { id: 'garage',   icon: '🚘', label: 'רכבים שקניתי',       value: ownedCount },
    { id: 'watches',  icon: '🔔', label: 'ההתראות שלי',       value: watchesCount },
    { id: 'referral', icon: '🤝', label: 'הפנה חבר',           value: referral?.count },
    { id: 'packages', icon: '🛒', label: 'רכישת מוצר',         value: packagesCount },
    { id: 'ticket',   icon: '🎫', label: 'תמיכה' },
    ...(user.is_admin ? [{ id: 'admin', icon: '🛠', label: 'פאנל ניהול' }] : []),
  ]

  const mainTiles = tiles.filter(t => !['ticket', 'admin'].includes(t.id))
  const adminTile = tiles.find(t => t.id === 'admin')
  const quotaPct = isUnlimited ? 100
    : user.searches_quota > 0 ? Math.max(4, Math.min(100, Math.round((searchesLeft / user.searches_quota) * 100)))
    : 0

  return (
    <div className="page" style={{ paddingBottom: 24 }}>
      <BackButton onClick={onBack} />

      {/* Identity */}
      <header style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
        <div style={{
          width: 60, height: 60, borderRadius: '50%', flexShrink: 0,
          background: 'linear-gradient(135deg, #007aff, #00c6ff)', color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 22, fontWeight: 800,
        }}>{initials(user.first_name, user.last_name)}</div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{
            fontSize: 22, fontWeight: 900, letterSpacing: '-0.5px',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{fullName}</div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2, lineHeight: 1.5 }}>
            {user.username && <div dir="ltr" style={{ textAlign: 'right' }}>@{user.username}</div>}
            {user.first_seen && <div>הצטרף/ה ב-{fmtDateLong(user.first_seen)}</div>}
          </div>
          <span style={{
            display: 'inline-block', maxWidth: '100%', marginTop: 6, borderRadius: 14, padding: '3px 10px', fontSize: 12, fontWeight: 700, lineHeight: 1.4,
            border: '1px solid var(--border)',
            background: isSubscriber ? 'rgba(0, 122, 255, 0.1)' : 'rgba(255,255,255,0.85)',
            color: isSubscriber ? 'var(--primary)' : 'var(--text-muted)',
          }}>{subLabel}</span>
        </div>
      </header>

      {/* Plan and quota */}
      <div className="card" style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>יתרת חיפושים</span>
          <span style={{
            fontSize: 26, fontWeight: 900, letterSpacing: '-0.5px',
            color: searchesLeft === 0 ? 'var(--danger)' : 'var(--text-main)',
          }}>{isUnlimited ? '∞' : searchesLeft}</span>
        </div>
        <div style={{ height: 8, borderRadius: 99, background: 'rgba(0, 100, 200, 0.1)', overflow: 'hidden' }}>
          <div style={{
            width: `${quotaPct}%`, height: '100%', borderRadius: 99,
            background: searchesLeft === 0 ? 'var(--danger)' : 'linear-gradient(90deg, #007aff, #00c6ff)',
          }} />
        </div>
        {isUnlimited && quotaExpires && (
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>בתוקף עד {fmtDate(quotaExpires)}</div>
        )}
        <button
          className={isSubscriber ? 'btn btn-outline' : 'btn'}
          style={{ marginTop: 2, padding: 12 }}
          onClick={() => onNavigate('packages')}
        >
          {isSubscriber ? 'חבילות ומנויים' : 'שדרג עכשיו'}
        </button>
      </div>

      {/* Navigation tiles */}
      <h3 className="section-label" style={{ marginTop: 8 }}>האזור שלי</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {mainTiles.map(t => (
          <button
            key={t.id}
            onClick={() => onNavigate(t.id)}
            className="card"
            style={{
              margin: 0, padding: '16px 14px', textAlign: 'right', cursor: 'pointer',
              display: 'flex', flexDirection: 'column', gap: 6, borderRadius: 18,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 26, lineHeight: 1 }}>{t.icon}</span>
              {t.value != null && (
                <span style={{
                  fontSize: 12, fontWeight: 700, color: 'var(--primary)',
                  background: 'rgba(0, 122, 255, 0.1)', borderRadius: 99, padding: '2px 9px',
                }}>{t.value}</span>
              )}
            </div>
            <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-main)' }}>{t.label}</span>
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginTop: 22 }}>
        {[{ id: 'ticket', label: 'תמיכה' }, { id: 'privacy', label: 'פרטיות' }, { id: 'howItWorks', label: 'איך זה עובד' }].map(l => (
          <button
            key={l.id}
            onClick={() => onNavigate(l.id)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer', fontSize: 13,
              color: 'var(--text-muted)', textDecoration: 'underline', padding: 4,
            }}
          >{l.label}</button>
        ))}
      </div>

      {adminTile && (
        <button
          onClick={() => onNavigate('admin')}
          style={{
            width: '100%', marginTop: 18, padding: '12px 14px', borderRadius: 14, cursor: 'pointer',
            border: '1px solid var(--border)', background: 'rgba(255,255,255,0.85)',
            color: 'var(--primary)', fontWeight: 700, fontSize: 14,
          }}
        >🛠 פאנל ניהול</button>
      )}
    </div>
  )
}
