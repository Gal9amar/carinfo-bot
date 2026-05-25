import paypalLogo from '../assets/paypal-logo.png'

function VisaLogo() {
  return (
    <svg viewBox="0 0 60 38" width="36" height="23" style={{ borderRadius: 4, display: 'block' }}>
      <rect width="60" height="38" rx="4" fill="#1a1f71"/>
      <text x="30" y="27" textAnchor="middle" fill="white" fontSize="20" fontFamily="Arial,sans-serif" fontStyle="italic" fontWeight="bold">VISA</text>
    </svg>
  )
}

function MastercardLogo() {
  return (
    <svg viewBox="0 0 60 38" width="36" height="23" style={{ borderRadius: 4, display: 'block' }}>
      <rect width="60" height="38" rx="4" fill="#252525"/>
      <circle cx="22" cy="19" r="11" fill="#EB001B"/>
      <circle cx="38" cy="19" r="11" fill="#F79E1B"/>
      <path d="M30 9.7 a11 11 0 0 1 0 18.6 a11 11 0 0 1 0-18.6z" fill="#FF5F00"/>
    </svg>
  )
}

function AmexLogo() {
  return (
    <svg viewBox="0 0 60 38" width="36" height="23" style={{ borderRadius: 4, display: 'block' }}>
      <rect width="60" height="38" rx="4" fill="#2E77BC"/>
      <text x="30" y="26" textAnchor="middle" fill="white" fontSize="13" fontFamily="Arial,sans-serif" fontWeight="bold" letterSpacing="1">AMEX</text>
    </svg>
  )
}

function IsracardLogo() {
  return (
    <svg viewBox="0 0 60 38" width="36" height="23" style={{ borderRadius: 4, display: 'block' }}>
      <rect width="60" height="38" rx="4" fill="#e85d00"/>
      <text x="30" y="24" textAnchor="middle" fill="white" fontSize="10" fontFamily="Arial,sans-serif" fontWeight="bold">ישראכרט</text>
    </svg>
  )
}

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
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 11, color: '#666', letterSpacing: 0.5 }}>או שלם עם כרטיס:</span>
          <VisaLogo />
          <MastercardLogo />
          <AmexLogo />
          <IsracardLogo />
        </div>
      </button>

      <div style={{ marginTop: 14, fontSize: 12, color: 'var(--hint)', textAlign: 'center' }}>
        לאחר השלמת התשלום הגישה תתעדכן אוטומטית ותגיע הודעה בצ'אט
      </div>
    </div>
  )
}
