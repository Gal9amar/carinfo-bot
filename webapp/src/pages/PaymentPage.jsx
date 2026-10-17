import { useState, useEffect, useRef } from 'react'
import { monthsLabel } from '../utils/plan.js'
import BackButton from '../components/BackButton.jsx'
import { initiatePayment, initiateProductPayment, fetchPaymentMethods } from '../api.js'
import paypalLogo     from '../assets/paypal-logo.webp'
import visaLogo       from '../assets/visa.svg'
import mastercardLogo from '../assets/mastercard.svg'
import amexLogo       from '../assets/amex.svg'
import isracardLogo   from '../assets/isracard.webp'

// Same rule as src/payment_methods.py::is_paypal
const isPaypalMethod = m => /paypal|פייפאל/i.test(m?.name || '')

const CARD_STYLE ={ height: 24, width: 'auto', borderRadius: 4, display: 'block', objectFit: 'contain' }

export default function PaymentPage({ pkg, onBack }) {
  const [busy, setBusy]            = useState(false)
  const orderRef = useRef(null)
  const [preparing, setPreparing]   = useState(true)
  const [extraMethods, setExtraMethods] = useState([])
  const [hasPaypal, setHasPaypal]   = useState(false)

  const qty        = pkg._qty ?? 1
  const totalPrice = pkg.price * qty
  const isAlerts   = pkg.package_type === 'alerts' || (pkg.label ?? '').includes('התראות')
  const desc       = pkg._isProduct
    ? (qty > 1 ? `×${qty} — ${pkg.description || pkg.delivery_time_note || ''}` : (pkg.description || pkg.delivery_time_note || ''))
    : isAlerts
      ? `${qty} התראה${qty > 1 ? 'ות' : ''} נוספת ביד2`
      : (pkg.searches === -1 ? `ללא הגבלה · ${monthsLabel(qty * Math.max(1, pkg.duration_months ?? 1))}` : `${(pkg.searches ?? 1) * qty} חיפושים`)

  // No order exists while the user is only looking at the payment methods. The order is created the
  // moment a method is chosen (and reused if they then pick another method on this screen).
  useEffect(() => {
    fetchPaymentMethods().catch(() => []).then(dbMethods => {
      // The list comes from the admin panel and contains ACTIVE methods only: the PayPal
      // button appears only when an active PayPal method exists, the rest are shown as-is.
      const list = Array.isArray(dbMethods) ? dbMethods : []
      setHasPaypal(list.some(isPaypalMethod))
      setExtraMethods(list.filter(m => !isPaypalMethod(m)))
      setPreparing(false)
    })
  }, [pkg.id])

  async function ensureOrder() {
    if (orderRef.current) return orderRef.current
    const data = await (pkg._isProduct ? initiateProductPayment(pkg.id, qty, false) : initiatePayment(pkg.id, qty, false))
    orderRef.current = data
    return data
  }

  async function pay(urlOf) {
    if (busy) return
    setBusy(true)
    try {
      const order = await ensureOrder()
      const url = urlOf(order)
      if (!url) { window.Telegram?.WebApp?.showAlert('אמצעי התשלום אינו זמין כרגע.'); return }
      if (window.Telegram?.WebApp?.openLink) window.Telegram.WebApp.openLink(url)
      else window.open(url, '_blank')
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה ביצירת הזמנה, נסה שוב.')
    } finally {
      setBusy(false)
    }
  }

  const openPaypal = () => pay(order => order.approval_url)
  const openManual = m => pay(() => m.payment_url)

  return (
    <div className="page">
      <BackButton onClick={onBack} label="חזרה" />

      <h1 className="page-title">💳 תשלום</h1>

      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="card-title">{pkg.label}</div>
          <div className="card-subtitle">{desc}</div>
        </div>
        <div style={{ fontSize: 28, fontWeight: 900, letterSpacing: '-1px', unicodeBidi: 'isolate', direction: 'ltr' }}>₪{totalPrice}</div>
      </div>

      {preparing ? (
        <div role="status" style={{ textAlign: 'center', padding: 24, color: 'var(--hint)', fontSize: 14 }}>
          ⏳ מכין קישור תשלום...
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {/* PayPal — always first, requires manual admin approval */}
          <h2 className="section-label" style={{ margin: '14px 4px 2px' }}>
            בחר אמצעי תשלום · אישור ידני, המנהל יאשר תוך זמן קצר
          </h2>
          {!hasPaypal && extraMethods.length === 0 && (
            <div role="status" className="card" style={{ textAlign: 'center', fontSize: 14 }}>
              אין כרגע אמצעי תשלום זמינים. נסו שוב מאוחר יותר או פנו לתמיכה.
            </div>
          )}
          {hasPaypal && <button
            onClick={openPaypal}
            disabled={busy}
            style={{
              width: '100%', display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', gap: 5,
              background: '#ffffff', border: '1px solid var(--border)', borderRadius: 18,
              padding: '10px 12px', cursor: busy ? 'default' : 'pointer',
              boxShadow: '0 4px 14px rgba(20, 60, 120, 0.06)',
              opacity: busy ? 0.7 : 1,
            }}
          >
            <img loading="lazy" decoding="async" src={paypalLogo} alt="PayPal" style={{ height: 28, objectFit: 'contain' }} />
            <span style={{ fontSize: 11, color: '#666' }}>או שלם באמצעות אשראי:</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <img loading="lazy" decoding="async" src={visaLogo}       alt="Visa"       style={CARD_STYLE} />
              <img loading="lazy" decoding="async" src={mastercardLogo} alt="Mastercard" style={CARD_STYLE} />
              <img loading="lazy" decoding="async" src={amexLogo}       alt="Amex"       style={CARD_STYLE} />
              <img loading="lazy" decoding="async" src={isracardLogo}   alt="Isracard"   style={CARD_STYLE} />
            </div>
          </button>}

          {/* Other active methods added by admin */}
          {extraMethods.length > 0 && (
            <>
              <div style={{ fontSize: 12, color: 'var(--hint)', paddingRight: 2, marginTop: 6 }}>
                ⏳ אישור ידני — המנהל יאשר תוך זמן קצר
              </div>
              {extraMethods.map(m => (
                <MethodButton key={m.id} m={m} disabled={busy} onClick={() => openManual(m)} />
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
        background: '#ffffff', border: '1px solid var(--border)', borderRadius: 18,
        padding: '12px 16px', cursor: disabled ? 'default' : 'pointer',
        boxShadow: '0 4px 14px rgba(20, 60, 120, 0.06)',
        opacity: disabled ? 0.5 : 1,
        transition: 'opacity 0.15s',
      }}
    >
      {m.logo_url
        ? <img loading="lazy" decoding="async" src={m.logo_url} alt={m.name} style={{ height: 32, objectFit: 'contain' }} onError={e => e.target.style.display='none'} />
        : <span style={{ fontSize: 22 }}>💳</span>
      }
      <span style={{ fontSize: 15, fontWeight: 700, color: '#111' }}>{m.name}</span>
    </button>
  )
}
