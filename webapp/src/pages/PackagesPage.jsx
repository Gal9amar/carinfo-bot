import { useState } from 'react'
import { initiatePayment } from '../api.js'

export default function PackagesPage({ packages, user, onSelect, onPrivacy, onSupport, onReferral }) {
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
      <div className="page-title">🛒 חנות חיפושים</div>

      {user && (
        <div className="card" style={{ marginBottom: 16 }}>
          <span style={{ fontSize: 14, color: 'var(--hint)' }}>
            שלום {user.first_name} · נותרו לך{' '}
            <strong>{user.searches_left === -1 ? '∞' : user.searches_left}</strong> חיפושים
          </span>
        </div>
      )}

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
            קבל חיפושים בחינם!
          </div>
          <div style={{ color: 'rgba(255,255,255,0.82)', fontSize: 13 }}>
            הפנה חברים וקבל חיפושים על כל הצטרפות ←
          </div>
        </div>
      </button>

      {packages.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14 }}>
          אין חבילות זמינות כרגע
        </div>
      )}

      {packages.map(pkg => {
        const qty = getQty(pkg.id)
        const isUnlimited = pkg.searches === -1
        const totalPrice = pkg.price * qty
        const totalSearches = isUnlimited ? '∞' : pkg.searches * qty

        return (
          <div key={pkg.id} style={{
            background: 'var(--bg2)',
            borderRadius: 16,
            overflow: 'hidden',
            marginBottom: 16,
            boxShadow: '0 2px 8px rgba(0,0,0,0.07)',
          }}>
            {/* Product image / placeholder */}
            {pkg.image_url ? (
              <img
                src={pkg.image_url}
                alt={pkg.label}
                style={{ width: '100%', height: 160, objectFit: 'cover', display: 'block' }}
              />
            ) : (
              <div style={{
                width: '100%', height: 120,
                background: isUnlimited
                  ? 'linear-gradient(135deg, #7928ca 0%, #ff0080 100%)'
                  : 'linear-gradient(135deg, var(--btn) 0%, #1a6aac 100%)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 52,
              }}>
                {isUnlimited ? '♾️' : '🔍'}
              </div>
            )}

            <div style={{ padding: 16 }}>
              <div style={{ fontSize: 17, fontWeight: 700, marginBottom: 4 }}>{pkg.label}</div>
              <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 14 }}>
                {isUnlimited ? 'חיפושים ללא הגבלת כמות' : `${pkg.searches} חיפושים לחבילה`}
              </div>

              {/* Quantity row — only for non-unlimited */}
              {!isUnlimited && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                  <div style={{
                    display: 'flex', alignItems: 'center',
                    background: 'var(--bg)', borderRadius: 10, overflow: 'hidden',
                    border: '1px solid rgba(0,0,0,0.07)',
                  }}>
                    <button
                      onClick={() => setQty(pkg.id, qty - 1)}
                      disabled={qty <= 1}
                      style={{
                        width: 40, height: 40, border: 'none', background: 'transparent',
                        fontSize: 22, lineHeight: 1, cursor: qty <= 1 ? 'default' : 'pointer',
                        color: qty <= 1 ? 'var(--hint)' : 'var(--btn)', fontWeight: 700,
                      }}
                    >−</button>
                    <span style={{ width: 38, textAlign: 'center', fontWeight: 700, fontSize: 16 }}>{qty}</span>
                    <button
                      onClick={() => setQty(pkg.id, qty + 1)}
                      disabled={qty >= 10}
                      style={{
                        width: 40, height: 40, border: 'none', background: 'transparent',
                        fontSize: 22, lineHeight: 1, cursor: qty >= 10 ? 'default' : 'pointer',
                        color: qty >= 10 ? 'var(--hint)' : 'var(--btn)', fontWeight: 700,
                      }}
                    >+</button>
                  </div>

                  <div style={{ textAlign: 'left', color: 'var(--hint)', fontSize: 13 }}>
                    סה״כ <strong style={{ color: 'var(--text)' }}>{totalSearches}</strong> חיפושים
                  </div>
                </div>
              )}

              {/* Price + buy */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                <div>
                  <span style={{ fontSize: 24, fontWeight: 800, color: 'var(--btn)' }}>₪{totalPrice}</span>
                  {qty > 1 && (
                    <span style={{ fontSize: 12, color: 'var(--hint)', marginRight: 6 }}>
                      ({qty} × ₪{pkg.price})
                    </span>
                  )}
                </div>
                <button
                  onClick={() => handleSelect(pkg)}
                  disabled={loading === pkg.id}
                  style={{
                    padding: '10px 22px', border: 'none', borderRadius: 12,
                    background: 'var(--btn)', color: 'var(--btn-text)',
                    fontSize: 15, fontWeight: 600, cursor: 'pointer',
                    opacity: loading === pkg.id ? 0.6 : 1,
                  }}
                >
                  {loading === pkg.id ? '⏳' : '🛒 רכישה'}
                </button>
              </div>
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
