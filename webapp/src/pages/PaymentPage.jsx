import { useState, useEffect } from 'react'
import { initiatePayment, promotePayment, fetchPaymentMethods } from '../api.js'

export default function PaymentPage({ pkg, onBack }) {
  const [paymentUrl, setPaymentUrl] = useState(null)
  const [paymentRef, setPaymentRef] = useState(null)
  const [preparing, setPreparing]   = useState(true)
  const [methods, setMethods]       = useState([])

  const qty = pkg._qty ?? 1
  const isAlerts = pkg.package_type === 'alerts' || (pkg.label ?? '').includes('התראות')
  const desc = isAlerts
    ? `${qty} התראה${qty > 1 ? 'ות' : ''} נוספת ביד2`
    : (pkg.searches === -1 ? 'ללא הגבלה' : `${(pkg.searches ?? 1) * qty} חיפושים`)

  useEffect(() => {
    fetchPaymentMethods().then(setMethods).catch(() => setMethods([]))
    initiatePayment(pkg.id, qty, true)
      .then(data => {
        setPaymentUrl(data.approval_url)
        setPaymentRef(data.ref)
        setPreparing(false)
      })
      .catch(() => {
        setPreparing(false)
        window.Telegram?.WebApp?.showAlert('שגיאה ביצירת הזמנה, נסה שוב.')
      })
  }, [pkg.id])

  function openMethod(url) {
    if (!url) return
    promotePayment(paymentRef)
    if (window.Telegram?.WebApp?.openLink) {
      window.Telegram.WebApp.openLink(url)
    } else {
      window.open(url, '_blank')
    }
  }

  // For PayPal-type methods we append the price; otherwise use URL as-is
  function resolvedUrl(m) {
    const u = m.payment_url || ''
    if (!u) return paymentUrl
    const lc = m.name.toLowerCase()
    if (lc.includes('paypal')) return `${u}/${pkg.price * qty}ILS`
    return u
  }

  return (
    <div className="page">
      <button
        className="btn btn-secondary"
        style={{ marginBottom: 16, width: 'auto', padding: '8px 16px' }}
        onClick={onBack}
      >
        ← חזרה
      </button>

      <div className="page-title">💳 תשלום</div>

      <div className="card">
        <div className="card-title">{pkg.label}</div>
        <div className="card-subtitle">{desc}</div>
        <div className="price-badge">₪{pkg.price * qty}</div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 14, lineHeight: 1.8 }}>
          <div>1️⃣ בחר אמצעי תשלום</div>
          <div>2️⃣ השלם את התשלום</div>
          <div>3️⃣ הגישה תתעדכן <strong>אוטומטית</strong> תוך שניות</div>
        </div>
      </div>

      {preparing && (
        <div style={{ textAlign: 'center', padding: 20, color: 'var(--hint)', fontSize: 14 }}>
          ⏳ מכין קישור תשלום...
        </div>
      )}

      {!preparing && methods.length === 0 && (
        <div style={{ textAlign: 'center', padding: 20, color: 'var(--hint)', fontSize: 13 }}>
          אין אמצעי תשלום זמינים כרגע
        </div>
      )}

      {!preparing && methods.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {methods.map(m => (
            <button
              key={m.id}
              onClick={() => openMethod(resolvedUrl(m))}
              disabled={!paymentUrl}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
                background: '#ffffff', border: '2px solid rgba(0,0,0,0.12)', borderRadius: 12,
                padding: '12px 16px', cursor: !paymentUrl ? 'default' : 'pointer',
                boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
                opacity: !paymentUrl ? 0.6 : 1,
                transition: 'opacity 0.15s',
              }}
            >
              {m.logo_url
                ? <img src={m.logo_url} alt={m.name} style={{ height: 32, objectFit: 'contain' }} onError={e => e.target.style.display='none'} />
                : <span style={{ fontSize: 22 }}>💳</span>
              }
              <span style={{ fontSize: 15, fontWeight: 700, color: '#111' }}>{m.name}</span>
            </button>
          ))}
        </div>
      )}

      <div style={{ marginTop: 14, fontSize: 12, color: 'var(--hint)', textAlign: 'center' }}>
        לאחר השלמת התשלום הגישה תתעדכן אוטומטית ותגיע הודעה בצ'אט
      </div>
    </div>
  )
}
