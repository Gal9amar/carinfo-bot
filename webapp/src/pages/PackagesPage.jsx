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

      {packages.map(pkg => {
        const qty          = getQty(pkg.id)
        const isUnlimited  = pkg.searches === -1
        const totalPrice   = pkg.price * qty
        const totalSearches = isUnlimited ? '∞' : pkg.searches * qty

        return (
          <div key={pkg.id} style={{
            background: 'var(--bg2)', borderRadius: 18,
            overflow: 'hidden', marginBottom: 20,
            boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
            border: '1px solid rgba(255,255,255,0.06)',
          }}>

            {/* Image */}
            {pkg.image_url ? (
              <img src={pkg.image_url} alt={pkg.label}
                style={{ width: '100%', height: 170, objectFit: 'cover', display: 'block' }} />
            ) : (
              <div style={{
                width: '100%', height: 130,
                background: isUnlimited
                  ? 'linear-gradient(135deg,#7928ca,#ff0080)'
                  : 'linear-gradient(135deg,#1a6aac,#0ea5e9)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 56,
              }}>{isUnlimited ? '♾️' : '⭐'}</div>
            )}

            {/* Name bar */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '14px 16px 0',
            }}>
              <div style={{ fontSize: 18, fontWeight: 800 }}>{pkg.label}</div>
              <span style={{
                fontSize: 11, fontWeight: 700, padding: '3px 10px',
                background: 'linear-gradient(135deg,#7928ca,#5a1e99)',
                color: '#fff', borderRadius: 20,
              }}>⭐ מנוי</span>
            </div>

            {/* Perks */}
            <div style={{ display: 'flex', gap: 8, padding: '10px 16px', flexWrap: 'wrap' }}>
              <Chip>{isUnlimited ? '♾️ ללא הגבלה' : `🔍 ${pkg.searches} חיפושים`}</Chip>
              <Chip>💳 תשלום חד-פעמי</Chip>
              <Chip>🔓 ללא תפוגה</Chip>
            </div>

            <div style={{ height: 1, background: 'var(--bg)', margin: '0 16px' }} />

            {/* Quantity — non-unlimited only */}
            {!isUnlimited && (
              <div style={{ padding: '12px 16px 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13, color: 'var(--hint)' }}>כמות</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 0,
                  background: 'var(--bg)', borderRadius: 12, overflow: 'hidden' }}>
                  <button onClick={() => setQty(pkg.id, qty - 1)} disabled={qty <= 1} style={{
                    width: 42, height: 38, border: 'none', background: 'transparent',
                    fontSize: 20, cursor: qty <= 1 ? 'default' : 'pointer',
                    color: qty <= 1 ? 'var(--hint)' : 'var(--btn)', fontWeight: 700,
                  }}>−</button>
                  <span style={{ width: 36, textAlign: 'center', fontWeight: 700, fontSize: 15 }}>{qty}</span>
                  <button onClick={() => setQty(pkg.id, qty + 1)} disabled={qty >= 10} style={{
                    width: 42, height: 38, border: 'none', background: 'transparent',
                    fontSize: 20, cursor: qty >= 10 ? 'default' : 'pointer',
                    color: qty >= 10 ? 'var(--hint)' : 'var(--btn)', fontWeight: 700,
                  }}>+</button>
                </div>
                <span style={{ fontSize: 13, color: 'var(--hint)' }}>
                  סה״כ <strong style={{ color: 'var(--text)' }}>{totalSearches}</strong> חיפושים
                </span>
              </div>
            )}

            {/* Price + CTA */}
            <div style={{ padding: '14px 16px 16px' }}>
              <div style={{ textAlign: 'center', marginBottom: 12 }}>
                <span style={{ fontSize: 34, fontWeight: 900, color: 'var(--btn)' }}>₪{totalPrice}</span>
                {qty > 1 && (
                  <span style={{ fontSize: 12, color: 'var(--hint)', marginRight: 8 }}>
                    ({qty} × ₪{pkg.price})
                  </span>
                )}
              </div>
              <button
                onClick={() => handleSelect(pkg)}
                disabled={loading === pkg.id}
                style={{
                  width: '100%', padding: '13px 0', border: 'none', borderRadius: 12,
                  background: 'var(--btn)', color: 'var(--btn-text)',
                  fontSize: 16, fontWeight: 700, cursor: 'pointer',
                  opacity: loading === pkg.id ? 0.6 : 1,
                  letterSpacing: 0.3,
                }}
              >{loading === pkg.id ? '⏳ מעבד...' : '🛒 לרכישה'}</button>
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

function Chip({ children }) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: '4px 10px',
      background: 'var(--bg)', borderRadius: 20,
      color: 'var(--hint)', border: '1px solid rgba(255,255,255,0.07)',
      whiteSpace: 'nowrap',
    }}>{children}</span>
  )
}
