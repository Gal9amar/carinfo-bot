import { useState, useEffect, useRef } from 'react'
import { startCryptoPayment, fetchCryptoStatus, refreshUserCache } from '../api.js'

const LABELS = { BINANCE_PAY: 'Binance Pay', USDT_TRC20: 'USDT (רשת TRC20)' }
const ERRORS = {
  method_disabled: 'שיטת התשלום הזו אינה זמינה כרגע.',
  busy: 'יש כרגע עומס בתשלומים, נסו שוב בעוד כמה דקות.',
  order_closed: 'ההזמנה כבר נסגרה. חזרו וצרו הזמנה חדשה.',
  blocked: 'החשבון חסום.',
}

function useCountdown(expiresAt) {
  const [left, setLeft] = useState(null)
  useEffect(() => {
    if (!expiresAt) return undefined
    const end = new Date(String(expiresAt).replace(' ', 'T') + 'Z').getTime()
    const tick = () => setLeft(Math.max(0, Math.round((end - Date.now()) / 1000)))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [expiresAt])
  return left
}

function CopyRow({ label, value, strong }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    try { navigator.clipboard?.writeText(String(value)) } catch { /* ignore */ }
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderTop: '1px solid var(--border)' }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{label}</div>
        <div dir="ltr" style={{
          fontFamily: 'monospace', fontWeight: strong ? 900 : 700, fontSize: strong ? 24 : 14,
          wordBreak: 'break-all', unicodeBidi: 'isolate', textAlign: 'right',
        }}>{value}</div>
      </div>
      <button type="button" className="btn btn-outline" onClick={copy}
        style={{ width: 'auto', margin: 0, padding: '8px 14px', minHeight: 40 }}>
        {copied ? '✓ הועתק' : 'העתק'}
      </button>
    </div>
  )
}

/** Shows the exact amount + destination of a crypto payment and waits for the automatic detection. */
export default function CryptoPayPanel({ method, ensureOrder, onClose }) {
  const [pay, setPay] = useState(null)
  const [err, setErr] = useState('')
  const [status, setStatus] = useState('pending')
  const startedRef = useRef(false)
  const left = useCountdown(pay?.expires_at)

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    ;(async () => {
      try {
        const order = await ensureOrder()
        setPay(await startCryptoPayment(order.ref, method))
      } catch (e) {
        setErr(ERRORS[e.message] || 'לא הצלחנו להתחיל את התשלום. נסו שוב.')
      }
    })()
  }, [method, ensureOrder])

  useEffect(() => {
    if (!pay || status !== 'pending') return undefined
    let alive = true
    const id = setInterval(async () => {
      try {
        const st = await fetchCryptoStatus(pay.ref)
        if (!alive) return
        if (st.status === 'confirmed') { setStatus('confirmed'); refreshUserCache() }
        else if (st.status !== 'pending') setStatus(st.status)
      } catch { /* keep polling */ }
    }, 5000)
    return () => { alive = false; clearInterval(id) }
  }, [pay, status])

  const mm = left == null ? '' : `${String(Math.floor(left / 60)).padStart(2, '0')}:${String(left % 60).padStart(2, '0')}`

  if (err) {
    return (
      <div className="card" role="alert" style={{ textAlign: 'center' }}>
        <div style={{ marginBottom: 10 }}>{err}</div>
        <button className="btn btn-outline" onClick={onClose}>חזרה לאמצעי התשלום</button>
      </div>
    )
  }
  if (!pay) return <div role="status" style={{ textAlign: 'center', padding: 24, color: 'var(--hint)' }}>⏳ יוצר פרטי תשלום...</div>

  if (status === 'confirmed') {
    return (
      <div className="card" role="status" style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 44 }} aria-hidden="true">✅</div>
        <div style={{ fontWeight: 900, fontSize: 18, margin: '6px 0' }}>התשלום זוהה!</div>
        <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>ההזמנה אושרה אוטומטית. ההטבה פעילה והודעה נשלחה בצ׳אט.</div>
        <button className="btn" style={{ marginTop: 14 }} onClick={onClose}>סיום</button>
      </div>
    )
  }
  if (status !== 'pending' || left === 0) {
    return (
      <div className="card" role="alert" style={{ textAlign: 'center' }}>
        <div style={{ fontWeight: 800, marginBottom: 6 }}>⏰ פג תוקף הבקשה</div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>
          אם כבר שלחתם את הסכום, פנו לתמיכה עם מזהה ההזמנה <span dir="ltr">{pay.ref}</span> ונאשר ידנית.
        </div>
        <button className="btn btn-outline" onClick={onClose}>חזרה</button>
      </div>
    )
  }

  const isPayId = pay.method === 'BINANCE_PAY'
  return (
    <div className="card">
      <div style={{ fontWeight: 800, fontSize: 16, marginBottom: 4 }}>🪙 תשלום ב-{LABELS[pay.method]}</div>
      <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 6 }}>
        שלחו <strong>בדיוק</strong> את הסכום המופיע למטה (כולל הסנטים) — כך נזהה את התשלום אוטומטית.
      </div>
      <CopyRow label="סכום לשליחה (USDT)" value={Number(pay.amount_usd).toFixed(2)} strong />
      {isPayId
        ? <CopyRow label="Binance Pay ID של היעד" value={pay.pay_id} />
        : <CopyRow label={`כתובת ארנק · רשת ${pay.network}`} value={pay.address} />}
      <div role="status" aria-live="polite" style={{ marginTop: 10, fontSize: 13, color: 'var(--text-muted)' }}>
        ⏳ ממתינים להפקדה… בתוקף עוד <span dir="ltr">{mm}</span>. אין צורך ללחוץ על כלום — האישור אוטומטי.
      </div>
      {!isPayId && (
        <div style={{ marginTop: 8, fontSize: 12, color: '#92400e' }}>
          ⚠️ שלחו רק USDT ברשת TRC20. שליחה ברשת אחרת או בסכום שונה לא תזוהה.
        </div>
      )}
      <button className="btn btn-outline" style={{ marginTop: 12 }} onClick={onClose}>ביטול / שיטה אחרת</button>
    </div>
  )
}
