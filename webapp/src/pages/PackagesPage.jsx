import { useState } from 'react'
import { initiatePayment } from '../api.js'
import BackButton from '../components/BackButton.jsx'

export default function PackagesPage({ packages, user, onSelect, onPrivacy, onSupport, onReferral, onBack }) {
  const [quantities, setQuantities] = useState({})
  const [loading, setLoading] = useState(null)

  function getQty(id) { return quantities[id] ?? 1 }
  function setQty(id, val) {
    setQuantities(q => ({ ...q, [id]: Math.max(1, Math.min(10, val)) }))
  }

  async function handleSelect(pkg) {
    const qty = getQty(pkg.id)
    setLoading(pkg.id)
    try {
      const data = await initiatePayment(pkg.id, qty)
      onSelect(data, data)
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה, נסה שוב.')
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="page" style={{ paddingBottom: 16 }}>
      {onBack && <BackButton onClick={onBack} />}
      <div className="page-title">⭐ רכישת מנוי</div>

      {user && (
        <div className="card" style={{ marginBottom: 16 }}>
          <span style={{ fontSize: 14, color: 'var(--hint)' }}>
            שלום {user.first_name} · נותרו לך{' '}
            <strong>{user.searches_left === -1 ? '∞' : user.searches_left}</strong> חיפושים
            {user.is_subscriber && (
              <span style={{
                marginRight: 8, fontSize: 11, fontWeight: 700,
                background: 'linear-gradient(135deg,#7928ca,#5a1e99)',
                color: '#fff', borderRadius: 20, padding: '2px 9px',
              }}>⭐ מנוי פעיל</span>
            )}
          </span>
        </div>
      )}

      {/* What is a subscription */}
      <div style={{
        background: 'linear-gradient(135deg,#7928ca18,#5a1e9908)',
        border: '1px solid #7928ca33',
        borderRadius: 16, padding: '16px 18px', marginBottom: 20,
      }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10, color: '#a855f7' }}>
          ⭐ מה זה מנוי CarInfo?
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 9, fontSize: 13 }}>
          <Row icon="🔍" text="מנוי מקנה לך סל חיפושים לשימוש בקצב שלך — ללא הגבלת זמן לניצול היתרה" />
          <Row icon="💰" text="גישה לנתונים המיועדים למנויים בלבד — ככל שיתווספו תכונות נוספות בעתיד, תיהנה מהן אוטומטית" />
          <Row icon="💳" text="תשלום חד-פעמי בלבד — אין חיוב חוזר, אין מנוי אוטומטי, אין הפתעות" />
          <Row icon="🔓" text="תוקף המנוי נשמר כל עוד יש לך יתרת חיפושים — יסתיים עם ניצול מלא" />
          <Row icon="➕" text='ניתן לרכוש כמה פעמים שרוצים ולצבור חיפושים — לחץ "+" לכמות מרובה' />
        </div>

        <div style={{
          marginTop: 14, padding: '10px 14px',
          background: 'rgba(56,161,105,0.12)', borderRadius: 10,
          fontSize: 12, color: '#38a169', fontWeight: 600,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span style={{ fontSize: 16 }}>✅</span>
          <span>כל רכישה מוכנסת לחשבונך תוך שעות ספורות לאחר אישור ידני ע"י המפעיל</span>
        </div>
      </div>

      {/* Free searches CTA */}
      <button
        onClick={onReferral}
        style={{
          display: 'flex', alignItems: 'center', gap: 14, width: '100%',
          background: 'linear-gradient(135deg, #38a169 0%, #276749 100%)',
          border: 'none', borderRadius: 16, padding: '14px 18px',
          marginBottom: 20, cursor: 'pointer', textAlign: 'right',
        }}
      >
        <span style={{ fontSize: 36, flexShrink: 0 }}>🎁</span>
        <div>
          <div style={{ color: '#fff', fontWeight: 700, fontSize: 16, marginBottom: 3 }}>
            רוצה חיפושים בחינם?
          </div>
          <div style={{ color: 'rgba(255,255,255,0.82)', fontSize: 13 }}>
            הפנה חברים וקבל חיפושים על כל הצטרפות ←
          </div>
          <div style={{ color: 'rgba(255,255,255,0.55)', fontSize: 11, marginTop: 3 }}>
            * חיפושים אלו אינם כוללים גישה לתכונות המיועדות למנויים
          </div>
        </div>
      </button>

      {packages.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14 }}>
          אין חבילות זמינות כרגע
        </div>
      )}

      {packages.map((pkg, idx) => {
        const qty           = getQty(pkg.id)
        const isUnlimited   = pkg.searches === -1
        const totalPrice    = pkg.price * qty
        const totalSearches = isUnlimited ? '∞' : pkg.searches * qty

        // Tier accent colours — cycle through silver / gold / platinum
        const tiers = [
          { grad: 'linear-gradient(135deg,#1e40af,#0ea5e9)', accent: '#38bdf8', label: '🥈 Silver' },
          { grad: 'linear-gradient(135deg,#92400e,#f59e0b)', accent: '#fbbf24', label: '🥇 Gold'   },
          { grad: 'linear-gradient(135deg,#4c1d95,#a855f7)', accent: '#c084fc', label: '💎 Platinum'},
        ]
        const tier = tiers[idx % tiers.length]

        return (
          <div key={pkg.id} style={{
            borderRadius: 20, overflow: 'hidden', marginBottom: 22,
            boxShadow: `0 6px 28px rgba(0,0,0,0.18), 0 0 0 1px rgba(255,255,255,0.07)`,
            background: 'var(--bg2)',
          }}>

            {/* ── Hero ── */}
            <div style={{ position: 'relative', height: pkg.image_url ? 170 : 150 }}>
              {pkg.image_url
                ? <img src={pkg.image_url} alt={pkg.label}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                : <div style={{ width: '100%', height: '100%', background: tier.grad,
                    display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                    <span style={{ fontSize: 52, lineHeight: 1 }}>{isUnlimited ? '♾️' : '⭐'}</span>
                    <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13, fontWeight: 600 }}>
                      {isUnlimited ? 'גישה ללא הגבלת כמות' : `${pkg.searches} חיפושים`}
                    </span>
                  </div>
              }
              {/* Dark overlay + tier badge at bottom-left of hero */}
              <div style={{
                position: 'absolute', inset: 0,
                background: 'linear-gradient(to top, rgba(0,0,0,0.72) 0%, transparent 55%)',
                display: 'flex', alignItems: 'flex-end',
                padding: '12px 14px',
              }}>
                <span style={{
                  fontSize: 13, fontWeight: 400, padding: '4px 12px',
                  background: tier.accent, color: '#000',
                  borderRadius: 20, whiteSpace: 'nowrap',
                }}>⭐ מנוי {tier.label.replace(/^[^\s]+\s/, '')}</span>
              </div>
            </div>

            {/* ── Perks row ── */}
            <div style={{
              display: 'flex', gap: 7, padding: '14px 14px 10px', flexWrap: 'wrap',
            }}>
              <Chip accent={tier.accent}>{isUnlimited ? '♾️ ללא הגבלה' : `🔍 ${pkg.searches} חיפושים`}</Chip>
              <Chip accent={tier.accent}>💳 חד-פעמי</Chip>
              <Chip accent={tier.accent}>🔓 ללא תפוגה</Chip>
            </div>

            <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0 14px' }} />

            {/* ── Quantity ── */}
            {!isUnlimited && (
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '12px 16px',
              }}>
                <span style={{ fontSize: 13, color: 'var(--hint)' }}>כמות</span>
                <div style={{ display: 'flex', alignItems: 'center',
                  background: 'var(--bg)', borderRadius: 12, overflow: 'hidden' }}>
                  <button onClick={() => setQty(pkg.id, qty - 1)} disabled={qty <= 1} style={{
                    width: 44, height: 40, border: 'none', background: 'transparent',
                    fontSize: 22, cursor: qty <= 1 ? 'default' : 'pointer',
                    color: qty <= 1 ? 'var(--hint)' : tier.accent, fontWeight: 700,
                  }}>−</button>
                  <span style={{ width: 34, textAlign: 'center', fontWeight: 800, fontSize: 16 }}>{qty}</span>
                  <button onClick={() => setQty(pkg.id, qty + 1)} disabled={qty >= 10} style={{
                    width: 44, height: 40, border: 'none', background: 'transparent',
                    fontSize: 22, cursor: qty >= 10 ? 'default' : 'pointer',
                    color: qty >= 10 ? 'var(--hint)' : tier.accent, fontWeight: 700,
                  }}>+</button>
                </div>
                <span style={{ fontSize: 13, color: 'var(--hint)' }}>
                  סה״כ <strong style={{ color: 'var(--text)' }}>{totalSearches}</strong>
                </span>
              </div>
            )}

            {/* ── Price + CTA ── */}
            <div style={{ padding: '10px 14px 16px' }}>
              <div style={{
                display: 'flex', alignItems: 'baseline', justifyContent: 'center',
                gap: 6, marginBottom: 12,
              }}>
                <span style={{ fontSize: 40, fontWeight: 900, color: tier.accent, lineHeight: 1 }}>
                  ₪{totalPrice}
                </span>
                {qty > 1 && (
                  <span style={{ fontSize: 12, color: 'var(--hint)' }}>({qty} × ₪{pkg.price})</span>
                )}
              </div>
              <button
                onClick={() => handleSelect(pkg)}
                disabled={loading === pkg.id}
                style={{
                  width: '100%', padding: '14px 0', border: 'none', borderRadius: 14,
                  background: tier.grad,
                  color: '#fff', fontSize: 16, fontWeight: 700,
                  cursor: 'pointer', opacity: loading === pkg.id ? 0.6 : 1,
                  boxShadow: `0 4px 14px rgba(0,0,0,0.25)`,
                  letterSpacing: 0.4,
                }}
              >{loading === pkg.id ? '⏳ מעבד...' : '🛒 רכישת מנוי'}</button>
            </div>
          </div>
        )
      })}

      {/* Nav buttons */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
        <button className="btn btn-secondary" style={{ marginTop: 0 }} onClick={onSupport}>
          🎫 תמיכה
        </button>
        <button className="btn btn-secondary" style={{ marginTop: 0 }} onClick={onReferral}>
          🤝 הפנה חבר
        </button>
      </div>

      <div style={{ textAlign: 'center', marginTop: 16 }}>
        <button
          onClick={onPrivacy}
          style={{ background: 'none', border: 'none', color: 'var(--hint)', fontSize: 12, cursor: 'pointer', textDecoration: 'underline' }}
        >
          מדיניות פרטיות ותנאי שימוש
        </button>
      </div>
    </div>
  )
}

function Row({ icon, text }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
      <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>{icon}</span>
      <span style={{ color: 'var(--text)', lineHeight: 1.5 }}>{text}</span>
    </div>
  )
}

function Chip({ children, accent }) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: '4px 10px',
      background: accent ? `${accent}18` : 'var(--bg)',
      borderRadius: 20, color: accent || 'var(--hint)',
      border: `1px solid ${accent ? `${accent}44` : 'rgba(255,255,255,0.07)'}`,
      whiteSpace: 'nowrap',
    }}>{children}</span>
  )
}
