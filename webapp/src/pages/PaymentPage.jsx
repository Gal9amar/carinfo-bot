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
          <div>1️⃣ לחץ על כפתור PayPal למטה</div>
          <div>2️⃣ השלם את התשלום</div>
          <div>3️⃣ חזור ולחץ "שילמתי ✓"</div>
        </div>
      </div>

      <button className="btn" onClick={openPayPal}>
        💳 שלם ₪{pkg.price} ב-PayPal
      </button>

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
