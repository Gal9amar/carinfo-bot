import { useState, useEffect } from 'react'
import { initiatePayment, promotePayment, fetchPaymentMethods } from '../api.js'
import paypalLogo from '../assets/paypal-logo.png'

const PAYPAL_METHOD = {
  id: '__paypal__',
  name: 'PayPal',
  logo_url: paypalLogo,
  payment_url: '',
  requires_manual_approval: false,
}

export default function PaymentPage({ pkg, onBack }) {
  const [paymentUrl, setPaymentUrl] = useState(null)
  const [paymentRef, setPaymentRef] = useState(null)
  const [preparing, setPreparing]   = useState(true)
  const [extraMethods, setExtraMethods] = useState([])

  const qty        = pkg._qty ?? 1
  const totalPrice = pkg.price * qty
  const isAlerts   = pkg.package_type === 'alerts' || (pkg.label ?? '').includes('התראות')
  const desc       = isAlerts
    ? `${qty} התראה${qty > 1 ? 'ות' : ''} נוספת ביד2`
    : (pkg.searches === -1 ? 'ללא הגבלה' : `${(pkg.searches ?? 1) * qty} חיפושים`)

  useEffect(() => {
    Promise.all([
      fetchPaymentMethods().catch(() => []),
      initiatePayment(pkg.id, qty, true).catch(() => null),
    ]).then(([dbMethods, data]) => {
      if (data) {
        setPaymentUrl(data.approval_url)
        setPaymentRef(data.ref)
      } else {
        window.Telegram?.WebApp?.showAlert('שגיאה ביצירת הזמנה, נסה שוב.')
      }
      // Only show DB methods that require manual approval (admin-added)
      setExtraMethods(dbMethods.filter(m => m.requires_manual_approval))
      setPreparing(false)
    })
  }, [pkg.id])

  function openPaypal() {
    if (!paymentUrl) return
    promotePayment(paymentRef)
    if (window.Telegram?.WebApp?.openLink) {
      window.Telegram.WebApp.openLink(paymentUrl)
    } else {
      window.open(paymentUrl, '_blank')
    }
  }

  function openManual(m) {
    if (!m.payment_url) return
    if (paymentRef) promotePayment(paymentRef)
    if (window.Telegram?.WebApp?.openLink) {
      window.Telegram.WebApp.openLink(m.payment_url)
    } else {
      window.open(m.payment_url, '_blank')
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
        <div className="price-badge">₪{totalPrice}</div>
      </div>

      {preparing ? (
        <div style={{ textAlign: 'center', padding: 24, color: 'var(--hint)', fontSize: 14 }}>
          ⏳ מכין קישור תשלום...
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {/* PayPal — always first, auto-approved */}
          <div style={{ fontSize: 12, color: 'var(--hint)', paddingRight: 2 }}>
            ✅ אישור אוטומטי — גישה מיידית לאחר התשלום
          </div>
          <MethodButton
            m={PAYPAL_METHOD}
            disabled={!paymentUrl}
            onClick={openPaypal}
          />

          {/* Manual methods added by admin */}
          {extraMethods.length > 0 && (
            <>
              <div style={{ fontSize: 12, color: 'var(--hint)', paddingRight: 2, marginTop: 6 }}>
                ⏳ אישור ידני — המנהל יאשר תוך זמן קצר
              </div>
              {extraMethods.map(m => (
                <MethodButton key={m.id} m={m} disabled={false} onClick={() => openManual(m)} />
              ))}
            </>
          )}
        </div>
      )}

      <div style={{ marginTop: 14, fontSize: 12, color: 'var(--hint)', textAlign: 'center' }}>
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
