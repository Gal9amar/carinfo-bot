import { useState, useEffect } from 'react'
import PageBanners from '../components/PageBanners.jsx'
import { fetchSearchHistory } from '../api.js'

const SUBTLE_BORDER = '1px solid rgba(0, 100, 200, 0.18)'

// Plate as typed: 7 digits -> 12-345-67, 8 digits -> 123-45-678
function formatPlateInput(raw) {
  const d = raw.replace(/\D/g, '').slice(0, 8)
  if (d.length <= 2) return d
  if (d.length <= 5) return `${d.slice(0, 2)}-${d.slice(2)}`
  if (d.length === 8) return `${d.slice(0, 3)}-${d.slice(3, 5)}-${d.slice(5)}`
  return `${d.slice(0, 2)}-${d.slice(2, 5)}-${d.slice(5)}`
}

function chipPlate(plate) {
  return formatPlateInput(String(plate))
}

export default function HomePage({ user, onNavigate, onSearchPlate }) {
  const [plateInput, setPlateInput] = useState('')
  const [recent, setRecent] = useState([])

  const searchesLeft = user?.searches_left
  const searchesQuota = user?.searches_quota
  const isUnlimited  = searchesLeft === -1
  const maintenance  = !!user?.maintenance
  // Admin is exempt server-side, so only block the search button for everyone else.
  const searchBlocked = maintenance && !user?.is_admin
  const digits = plateInput.replace(/\D/g, '')

  useEffect(() => {
    if (!user) return
    let alive = true
    fetchSearchHistory()
      .then(items => {
        if (!alive || !Array.isArray(items)) return
        setRecent(items.slice(0, 6).map(i => (typeof i === 'string' ? { plate: i } : i)))
      })
      .catch(() => {})
    return () => { alive = false }
  }, [user?.id])

  function handleSearch() {
    if (digits.length >= 5 && !searchBlocked) onSearchPlate(digits)
  }

  const quotaPct = isUnlimited ? 100
    : searchesQuota > 0 ? Math.max(4, Math.min(100, Math.round((searchesLeft / searchesQuota) * 100)))
    : 0

  const tiles = [
    { id: 'history',  icon: '📄', label: 'הדוחות שלי',  sub: 'חיפושי עבר' },
    user?.show_watch
      ? { id: 'watches', icon: '🔔', label: 'התראות יד2', sub: 'מודעות חדשות' }
      : { id: 'orders',  icon: '💳', label: 'הזמנות שלי', sub: 'היסטוריית רכישות' },
    { id: 'referral', icon: '🎁', label: 'קרדיט חינם',   sub: 'הפנה חברים' },
    { id: 'packages', icon: '📦', label: 'חבילות',       sub: 'חיפושים והתראות' },
  ]

  const links = [
    user?.show_watch && { id: 'orders', label: 'הזמנות' },
    { id: 'ticket',  label: 'תמיכה' },
    { id: 'privacy', label: 'פרטיות' },
    { id: 'accessibility', label: 'נגישות' },
  ].filter(Boolean)

  return (
    <div className="page" style={{ paddingBottom: 24 }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '-0.2px' }}>
            CarInfo<span style={{ color: 'var(--primary)' }}>.ai</span>
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 900, letterSpacing: '-0.5px' }}>
            {user?.first_name ? `שלום, ${user.first_name}` : 'שלום'}
          </h1>
        </div>
      </header>

      {maintenance && (
        <div
          role="status"
          className="card"
          style={{
            display: 'flex', gap: 12, alignItems: 'center', padding: '14px 16px',
            background: 'rgba(255, 149, 0, 0.12)', border: '1px solid rgba(255, 149, 0, 0.35)',
          }}
        >
          <div style={{ fontSize: 24 }} aria-hidden="true">🔧</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 15, color: '#b45309' }}>השירות בתחזוקה כרגע</div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
              {user?.is_admin ? 'מצב תחזוקה פעיל — החיפוש פתוח עבורך כמנהל' : 'חיפוש רכבים זמנית אינו זמין. נחזור בקרוב!'}
            </div>
          </div>
        </div>
      )}

      <div className="card" style={{ padding: 20, border: SUBTLE_BORDER }}>
        <h2 style={{ margin: '0 0 4px', fontWeight: 700, fontSize: 20 }}>בדיקת רכב</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: 14, margin: '0 0 16px', lineHeight: 1.5 }}>
          מספר רישוי, וזה הכל. דוח היסטוריה, בעלות ושעבודים תוך שניות.
        </p>

        <form
          onSubmit={e => { e.preventDefault(); handleSearch() }}
          style={{ margin: 0 }}
        >
          <div className="plate-input-wrap" style={{
            display: 'flex', direction: 'ltr', height: 64, borderRadius: 10, overflow: 'hidden',
            border: '3px solid #111', background: '#FFE500',
          }}>
            <div style={{
              width: 38, background: '#0a3fa8', color: '#fff', display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 800, lineHeight: 1.1,
            }}>
              <span style={{ fontSize: 14 }}>🇮🇱</span>
              <span>IL</span>
            </div>
            <input
              type="tel"
              inputMode="numeric"
              aria-label="מספר רישוי"
              placeholder="12-345-67"
              maxLength={10}
              value={plateInput}
              onChange={e => setPlateInput(formatPlateInput(e.target.value))}
              style={{
                flex: 1, minWidth: 0, border: 0, outline: 'none', background: 'transparent',
                textAlign: 'center', fontFamily: '"Arial Black", Arial, sans-serif', fontWeight: 900,
                fontSize: 30, letterSpacing: 3, color: '#111',
              }}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ marginTop: 14 }}
            disabled={digits.length < 5 || searchBlocked}
          >
            חפש רכב
          </button>
        </form>
      </div>

      {user && (
        <button
          onClick={() => onNavigate('packages')}
          className="card"
          style={{
            display: 'block', width: '100%', textAlign: 'right', cursor: 'pointer',
            padding: '14px 16px', border: SUBTLE_BORDER,
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
            <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-main)' }}>
              {isUnlimited ? 'מנוי ללא הגבלה' : `${searchesLeft} בדיקות נותרו`}
            </span>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--primary)' }}>
              {isUnlimited ? 'פרטי המנוי' : 'הוסף בדיקות'}
            </span>
          </div>
          <div aria-hidden="true" style={{ height: 8, borderRadius: 99, background: 'rgba(0, 100, 200, 0.1)', overflow: 'hidden' }}>
            <div style={{
              width: `${quotaPct}%`, height: '100%', borderRadius: 99,
              background: 'linear-gradient(90deg, #0066d6, #00c6ff)',
            }} />
          </div>
        </button>
      )}

      <PageBanners page="home" onNavigate={onNavigate} />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {tiles.map(t => (
          <button
            key={t.id}
            onClick={() => onNavigate(t.id)}
            className="card"
            style={{
              margin: 0, padding: '16px 14px', textAlign: 'right', cursor: 'pointer',
              display: 'flex', flexDirection: 'column', gap: 6,
              border: SUBTLE_BORDER, borderRadius: 18,
            }}
          >
            <span style={{ fontSize: 26, lineHeight: 1 }} aria-hidden="true">{t.icon}</span>
            <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-main)' }}>{t.label}</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t.sub}</span>
          </button>
        ))}
      </div>

      {recent.length > 0 && (
        <>
          <h3 className="section-label">חיפושים אחרונים</h3>
          <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4, scrollbarWidth: 'none' }}>
            {recent.map(r => (
              <button
                key={r.plate}
                onClick={() => !searchBlocked && onSearchPlate(String(r.plate).replace(/\D/g, ''))}
                aria-label={`חיפוש חוזר של רכב ${String(r.plate).replace(/\D/g, '')}`}
                className="plate-chip"
              >
                {chipPlate(r.plate)}
              </button>
            ))}
          </div>
        </>
      )}

      <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginTop: 24 }}>
        {links.map(l => (
          <button
            key={l.id}
            onClick={() => onNavigate(l.id)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer', fontSize: 13,
              color: 'var(--text-muted)', textDecoration: 'underline', padding: 4,
            }}
          >
            {l.label}
          </button>
        ))}
      </div>
    </div>
  )
}
