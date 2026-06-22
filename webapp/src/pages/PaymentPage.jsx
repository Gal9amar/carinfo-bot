import { useState, useEffect } from 'react'
import { initiatePayment, promotePayment, fetchPaymentMethods } from '../api.js'

export default function PaymentPage({ pkg, onBack }) {
  const [paymentUrl, setPaymentUrl] = useState(null)
  const [paymentRef, setPaymentRef] = useState(null)
  const [preparing, setPreparing]   = useState(true)
  const [methods, setMethods]       = useState([])

  const qty        = pkg._qty ?? 1
  const totalPrice = pkg.price * qty
  const isAlerts   = pkg.package_type === 'alerts' || (pkg.label ?? '').includes('התראות')
  const desc       = isAlerts
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

  function openMethod(m) {
    let url
    if (!m.requires_manual_approval) {
      // Auto-approved (PayPal) — use the approval_url from the API
      url = paymentUrl
      if (!url) return
      promotePayment(paymentRef)
    } else {
      // Manual approval — open the payment URL directly, no PayPal order needed
      url = m.payment_url
      if (!url) return
      // Still promote so admin gets notified
      if (paymentRef) promotePayment(paymentRef)
    }
    if (window.Telegram?.WebApp?.openLink) {
      window.Telegram.WebApp.openLink(url)
    } else {
      window.open(url, '_blank')
    }
  }

  const autoMethods   = methods.filter(m => !m.requires_manual_approval)
  const manualMethods = methods.filter(m => m.requires_manual_approval)

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
        <div className="price-badge">₪{totalPrice}</div>
      </div>

      {preparing ? (
        <div style={{ textAlign: 'center', padding: 24, color: 'var(--hint)', fontSize: 14 }}>
          ⏳ מכין קישור תשלום...
        </div>
      ) : (
        <>
          {autoMethods.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 8, paddingRight: 2 }}>
                ✅ אישור אוטומטי — גישה מיידית לאחר התשלום
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {autoMethods.map(m => (
                  <MethodButton key={m.id} m={m} disabled={!paymentUrl} onClick={() => openMethod(m)} />
                ))}
              </div>
            </div>
          )}

          {manualMethods.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 8, paddingRight: 2 }}>
                ⏳ אישור ידני — המנהל יאשר תוך זמן קצר
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {manualMethods.map(m => (
                  <MethodButton key={m.id} m={m} disabled={false} onClick={() => openMethod(m)} />
                ))}
              </div>
            </div>
          )}

          {methods.length === 0 && (
            <div style={{ textAlign: 'center', padding: 20, color: 'var(--hint)', fontSize: 13 }}>
              אין אמצעי תשלום זמינים כרגע
            </div>
          )}
        </>
      )}

      <div style={{ marginTop: 8, fontSize: 12, color: 'var(--hint)', textAlign: 'center' }}>
        לאחר השלמת התשלום הגישה תתעדכן ותגיע הודעה בצ'אט
      </div>
    </div>
  )
}

function MethodButton({ m, disabled, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
        background: '#ffffff', border: '2px solid rgba(0,0,0,0.1)', borderRadius: 12,
        padding: '12px 16px', cursor: disabled ? 'default' : 'pointer',
        boxShadow: '0 2px 10px rgba(0,0,0,0.12)',
        opacity: disabled ? 0.5 : 1,
        transition: 'opacity 0.15s',
      }}
    >
      {m.logo_url
        ? <img src={m.logo_url} alt={m.name} style={{ height: 32, objectFit: 'contain' }} onError={e => e.target.style.display='none'} />
        : <span style={{ fontSize: 22 }}>💳</span>
      }
      <span style={{ fontSize: 15, fontWeight: 700, color: '#111' }}>{m.name}</span>
    </button>
  )
}
