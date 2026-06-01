import { useState, useEffect } from 'react'
import { initiatePayment, promotePayment } from '../api.js'
import paypalLogo    from '../assets/paypal-logo.png'
import visaLogo      from '../assets/visa.svg'
import mastercardLogo from '../assets/mastercard.svg'
import amexLogo      from '../assets/amex.svg'
import isracardLogo  from '../assets/isracard.png'

const CARD_STYLE = { height: 24, width: 'auto', borderRadius: 4, display: 'block', objectFit: 'contain' }

export default function PaymentPage({ pkg, onBack }) {
  const [paymentUrl, setPaymentUrl] = useState(null)
  const [paymentRef, setPaymentRef] = useState(null)
  const [preparing, setPreparing] = useState(true)
  const qty = pkg._qty ?? 1
  const isAlerts = pkg.package_type === 'alerts' || (pkg.label ?? '').includes('התראות')
  const desc = isAlerts
    ? `${qty} התראה${qty > 1 ? 'ות' : ''} נוספת ביד2`
    : (pkg.searches === -1 ? 'ללא הגבלה' : `${(pkg.searches ?? 1) * qty} חיפושים`)

  useEffect(() => {
    // intent_only=true: creates PayPal order silently (no admin notification, not in history)
    initiatePayment(pkg.id, qty, true)
      .then(data => {
        setPaymentUrl(data.approval_url)
        setPaymentRef(data.ref)
        setPreparing(false)
      })
      .catch(err => {
        console.error('payment initiate error:', err)
        setPreparing(false)
        window.Telegram?.WebApp?.showAlert('שגיאה ביצירת הזמנה, נסה שוב.')
      })
  }, [pkg.id])

  function openPayPal() {
    if (!paymentUrl) return
    // Fire-and-forget: promotes order to 'created', notifies admin, adds to history
    promotePayment(paymentRef)
    // Synchronous openLink — no await before this call
    if (window.Telegram?.WebApp?.openLink) {
      window.Telegram.WebApp.openLink(paymentUrl)
    } else {
      window.open(paymentUrl, '_blank')
    }
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
        <div className="price-badge">₪{pkg.price}</div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 14, lineHeight: 1.8 }}>
          <div>1️⃣ לחץ על הלחצן למטה</div>
          <div>2️⃣ שלם עם <strong>PayPal</strong> או <strong>כרטיס אשראי</strong></div>
          <div>3️⃣ הגישה תתעדכן <strong>אוטומטית</strong> תוך שניות</div>
        </div>
      </div>

      <button
        onClick={openPayPal}
        disabled={preparing || !paymentUrl}
        style={{
          width: '100%', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 5,
          background: '#ffffff', border: '2px solid #003087', borderRadius: 12,
          padding: '10px 12px', cursor: (preparing || !paymentUrl) ? 'default' : 'pointer',
          boxShadow: '0 2px 12px rgba(0,0,0,0.18)',
          opacity: (preparing || !paymentUrl) ? 0.7 : 1,
        }}
      >
        {preparing
          ? <span style={{ fontSize: 14, color: '#003087' }}>⏳ מכין קישור תשלום...</span>
          : <>
              <img src={paypalLogo} alt="PayPal" style={{ height: 28, objectFit: 'contain' }} />
              <span style={{ fontSize: 11, color: '#666' }}>או שלם באמצעות אשראי:</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <img src={visaLogo}        alt="Visa"       style={CARD_STYLE} />
                <img src={mastercardLogo}  alt="Mastercard" style={CARD_STYLE} />
                <img src={amexLogo}        alt="Amex"       style={CARD_STYLE} />
                <img src={isracardLogo}    alt="Isracard"   style={CARD_STYLE} />
              </div>
            </>
        }
      </button>

      <div style={{ marginTop: 14, fontSize: 12, color: 'var(--hint)', textAlign: 'center' }}>
        לאחר השלמת התשלום הגישה תתעדכן אוטומטית ותגיע הודעה בצ'אט
      </div>
    </div>
  )
}
