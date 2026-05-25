import paypalLogo   from '../assets/paypal-logo.png'
import visaLogo      from '../assets/visa.svg'
import mastercardLogo from '../assets/mastercard.svg'
import amexLogo      from '../assets/amex.svg'
import isracardLogo  from '../assets/isracard.svg'

const CARD_STYLE = { height: 24, width: 'auto', borderRadius: 4, display: 'block', objectFit: 'contain' }

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
          <div>1️⃣ לחץ על הלחצן למטה</div>
          <div>2️⃣ שלם עם <strong>PayPal</strong> או <strong>כרטיס אשראי</strong></div>
          <div>3️⃣ הגישה תעודכן <strong>אוטומטית</strong> תוך שניות</div>
        </div>
      </div>

      <button
        onClick={openPayPal}
        style={{
          width: '100%', display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 10,
          background: '#ffffff', border: '2px solid #003087', borderRadius: 12,
          padding: '16px 12px', cursor: 'pointer',
          boxShadow: '0 2px 12px rgba(0,0,0,0.18)',
        }}
      >
        <img src={paypalLogo} alt="PayPal" style={{ height: 28, objectFit: 'contain' }} />
        <span style={{ fontSize: 11, color: '#666' }}>או שלם עם כרטיס:</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <img src={visaLogo}       alt="Visa"       style={CARD_STYLE} />
          <img src={mastercardLogo} alt="Mastercard" style={CARD_STYLE} />
          <img src={amexLogo}       alt="Amex"       style={CARD_STYLE} />
          <img src={isracardLogo}   alt="Isracard"   style={CARD_STYLE} />
        </div>
      </button>

      <div style={{ marginTop: 14, fontSize: 12, color: 'var(--hint)', textAlign: 'center' }}>
        לאחר השלמת התשלום הגישה תתעדכן אוטומטית ותגיע הודעה בצ'אט
      </div>
    </div>
  )
}
