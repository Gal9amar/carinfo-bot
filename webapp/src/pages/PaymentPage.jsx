import paypalLogo from '../assets/paypal-logo.png'

export default function PaymentPage({ pkg, paymentData, onBack }) {
  const desc = pkg.searches === -1 ? 'ללא הגבלה' : `${pkg.searches} חיפושים`

  function openPayPal() {
    const url = paymentData.approval_url
    if (window.Telegram?.WebApp?.openLink) {
      window.Telegram.WebApp.openLink(url)
    } else {
      window.open(url, '_blank')
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
        <div className="price-badge">₪{paymentData.price}</div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 14, lineHeight: 1.8 }}>
          <div>1️⃣ לחץ על לחצן PayPal למטה</div>
          <div>2️⃣ השלם את התשלום בדף PayPal</div>
          <div>3️⃣ הגישה תעודכן <strong>אוטומטית</strong> תוך שניות</div>
        </div>
      </div>

      <button
        onClick={openPayPal}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: '#ffffff', border: '2px solid #003087', borderRadius: 12,
          padding: '16px 8px', cursor: 'pointer',
          boxShadow: '0 2px 12px rgba(0,0,0,0.18)',
        }}
      >
        <img src={paypalLogo} alt="PayPal" style={{ height: 32, objectFit: 'contain' }} />
      </button>

      <div style={{ marginTop: 14, fontSize: 12, color: 'var(--hint)', textAlign: 'center' }}>
        לאחר השלמת התשלום ב-PayPal, הגישה תתעדכן אוטומטית ותקבל הודעה בצ'אט
      </div>
    </div>
  )
}
