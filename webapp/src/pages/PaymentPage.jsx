import { useState } from 'react'
import { confirmPayment } from '../api.js'

export default function PaymentPage({ pkg, paymentData, onBack, onDone }) {
  const [confirming, setConfirming] = useState(false)
  const [paid, setPaid] = useState(false)

  const desc = pkg.searches === -1 ? 'ללא הגבלה' : `${pkg.searches} חיפושים`

  function openPayPal() {
    window.open(paymentData.paypal_url, '_blank')
    setPaid(true)
  }

  function openPayBox() {
    window.open(paymentData.paybox_url, '_blank')
    setPaid(true)
  }

  async function handleConfirm() {
    setConfirming(true)
    try {
      await confirmPayment(paymentData.ref, pkg.id)
      onDone()
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה בשליחת האישור. נסה שוב.')
    } finally {
      setConfirming(false)
    }
  }

  return (
    <div className="page">
      <button className="btn btn-secondary" style={{ marginBottom: 16, width: 'auto', padding: '8px 16px' }} onClick={onBack}>
        ← חזרה
      </button>

      <div className="page-title">💳 תשלום</div>

      <div className="card">
        <div className="card-title">{pkg.label}</div>
        <div className="card-subtitle">{desc}</div>
        <div className="price-badge">₪{pkg.price}</div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 14, lineHeight: 1.6 }}>
          <div>1️⃣ בחר שיטת תשלום למטה</div>
          <div>2️⃣ השלם את התשלום</div>
          <div>3️⃣ חזור ולחץ "שילמתי ✓"</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={openPayPal}
          style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: '#003087', border: 'none', borderRadius: 12, padding: '14px 8px',
            cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.18)',
          }}
        >
          <img src="/paypal-logo.png" alt="PayPal" style={{ height: 28, objectFit: 'contain' }} />
        </button>
        <button
          onClick={openPayBox}
          style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: '#ffffff', border: '2px solid #29abe2', borderRadius: 12, padding: '14px 8px',
            cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,0.10)',
          }}
        >
          <img src="/paybox-logo.webp" alt="PayBox" style={{ height: 28, objectFit: 'contain' }} />
        </button>
      </div>

      {paid && (
        <button
          className="btn btn-success"
          style={{ marginTop: 8 }}
          disabled={confirming}
          onClick={handleConfirm}
        >
          {confirming ? '...' : '✅ שילמתי — שלח אישור'}
        </button>
      )}
    </div>
  )
}
