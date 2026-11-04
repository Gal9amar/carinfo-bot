import { useState, useEffect, useRef } from 'react'
import { startCryptoPayment, verifyCryptoPayment, refreshUserCache } from '../api.js'

const LABELS = { BINANCE_PAY: 'Binance Pay', USDT_TRC20: 'USDT (רשת TRC20)' }
const START_ERRORS = {
  method_disabled: 'שיטת התשלום הזו אינה זמינה כרגע.',
  order_closed: 'ההזמנה כבר נסגרה. חזרו וצרו הזמנה חדשה.',
  blocked: 'החשבון חסום.',
}

function verifyMessage(res, method) {
  const left = res.attempts_left != null ? ` (נותרו ${res.attempts_left} ניסיונות)` : ''
  switch (res.error) {
    case 'bad_format':
      return method === 'USDT_TRC20'
        ? 'המזהה לא נראה תקין. יש להדביק את ה-TX Hash המלא של ההעברה (64 תווים, אותיות a-f וספרות).'
        : 'המזהה לא נראה תקין. יש להדביק את ה-Order ID / Transaction ID מהקבלה של Binance Pay.'
    case 'not_found':
      return `לא מצאנו עסקה כזו אצלנו. ודאו שהעברתם ליעד הנכון ושהעסקה הושלמה, ונסו שוב בעוד רגע.${left}`
    case 'wrong_currency': return `המטבע ששולם (${res.currency}) לא נתמך. יש לשלם ב-USDT.${left}`
    case 'amount_low': return `הסכום שהתקבל (${res.got}$) נמוך מהנדרש (${res.expected}$).${left}`
    case 'too_old': return `העסקה בוצעה לפני שפתחתם את הבקשה, ולכן לא ניתן להשתמש בה.${left}`
    case 'used': return 'העסקה הזו כבר נוצלה. אם לדעתכם זו טעות — פנו לתמיכה.'
    case 'expired': return 'פג תוקף הבקשה. חזרו לאמצעי התשלום ופתחו בקשה חדשה.'
    case 'order_closed': return 'ההזמנה כבר נסגרה.'
    case 'too_many_attempts': return 'יותר מדי ניסיונות. פנו לתמיכה עם מזהה ההזמנה ונאשר ידנית.'
    case 'api_error': return `לא הצלחנו להתחבר לשירות האימות כרגע. נסו שוב בעוד דקה.${left}`
    case 'approve_failed': return 'התשלום אומת אך האישור נכשל. פנו לתמיכה — המנהל קיבל התראה.'
    default: return 'האימות נכשל. נסו שוב.'
  }
}

function CopyRow({ label, value, strong, display }) {
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
        }}>{display ?? value}</div>
      </div>
      <button type="button" className="btn btn-outline" onClick={copy}
        style={{ width: 'auto', margin: 0, padding: '8px 14px', minHeight: 40 }}>
        {copied ? '✓ הועתק' : 'העתק'}
      </button>
    </div>
  )
}

/** Amount + destination of a crypto payment; the buyer pastes the transaction id and it is verified automatically. */
export default function CryptoPayPanel({ method, ensureOrder, onClose }) {
  const [pay, setPay] = useState(null)
  const [err, setErr] = useState('')
  const [txId, setTxId] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const [done, setDone] = useState(false)
  const startedRef = useRef(false)

  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true
    ;(async () => {
      try {
        const order = await ensureOrder()
        setPay(await startCryptoPayment(order.ref, method))
      } catch (e) {
        setErr(START_ERRORS[e.message] || 'לא הצלחנו להתחיל את התשלום. נסו שוב.')
      }
    })()
  }, [method, ensureOrder])

  async function verify(e) {
    e?.preventDefault()
    if (busy || !txId.trim()) return
    setBusy(true); setMsg('')
    try {
      const res = await verifyCryptoPayment(pay.ref, txId.trim())
      if (res.ok) { setDone(true); refreshUserCache() }
      else setMsg(verifyMessage(res, method))
    } catch {
      setMsg('שגיאת תקשורת. נסו שוב.')
    }
    setBusy(false)
  }

  if (err) {
    return (
      <div className="card" role="alert" style={{ textAlign: 'center' }}>
        <div style={{ marginBottom: 10 }}>{err}</div>
        <button className="btn btn-outline" onClick={onClose}>חזרה לאמצעי התשלום</button>
      </div>
    )
  }
  if (!pay) return <div role="status" style={{ textAlign: 'center', padding: 24, color: 'var(--hint)' }}>⏳ יוצר פרטי תשלום...</div>

  if (done) {
    return (
      <div className="card" role="status" style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 44 }} aria-hidden="true">✅</div>
        <div style={{ fontWeight: 900, fontSize: 18, margin: '6px 0' }}>התשלום אומת!</div>
        <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>ההזמנה אושרה אוטומטית. ההטבה פעילה והודעה נשלחה בצ׳אט.</div>
        <button className="btn" style={{ marginTop: 14 }} onClick={onClose}>סיום</button>
      </div>
    )
  }

  const isPayId = pay.method === 'BINANCE_PAY'
  return (
    <div className="card">
      <div style={{ fontWeight: 800, fontSize: 16, marginBottom: 4 }}>🪙 תשלום ב-{LABELS[pay.method]}</div>
      <ol style={{ margin: '6px 18px 6px 0', padding: 0, fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.7 }}>
        <li>שלחו לפחות את הסכום המופיע למטה ל{isPayId ? '-Pay ID' : 'כתובת'} שלנו.</li>
        <li>העתיקו את {isPayId ? 'ה-Order ID / Transaction ID מהקבלה ב-Binance' : 'ה-TX Hash של ההעברה מהארנק'}.</li>
        <li>הדביקו אותו כאן ולחצו "אמת תשלום" — האישור אוטומטי.</li>
      </ol>
      <CopyRow label="סכום לשליחה (USDT)" value={Number(pay.amount_usd).toFixed(2)} display={`$${Number(pay.amount_usd).toFixed(2)}`} strong />
      {isPayId
        ? <CopyRow label="Binance Pay ID של היעד" value={pay.pay_id} />
        : <CopyRow label={`כתובת ארנק · רשת ${pay.network}`} value={pay.address} />}
      {!isPayId && (
        <div style={{ marginTop: 6, fontSize: 12, color: '#92400e' }}>
          ⚠️ שלחו רק USDT ברשת TRC20. שליחה ברשת אחרת לא תזוהה.
        </div>
      )}

      <form onSubmit={verify} style={{ marginTop: 14 }}>
        <label htmlFor="crypto-tx" style={{ fontSize: 13, fontWeight: 700 }}>
          {isPayId ? 'Order ID / Transaction ID' : 'TX Hash'}
        </label>
        <input id="crypto-tx" className="input" dir="ltr" value={txId} onChange={e => setTxId(e.target.value)}
          placeholder={isPayId ? 'לדוגמה: 12345678901234567890' : '64 תווים (a-f, 0-9)'}
          autoComplete="off" autoCapitalize="off" spellCheck={false}
          style={{ marginTop: 6, fontFamily: 'monospace' }} />
        <button className="btn" type="submit" disabled={busy || !txId.trim()} style={{ marginTop: 10 }}>
          {busy ? '⏳ מאמת...' : 'אמת תשלום'}
        </button>
      </form>
      <div role="status" aria-live="polite" style={{ marginTop: 8, fontSize: 13, color: '#c53030', minHeight: 18 }}>{msg}</div>

      <button className="btn btn-outline" style={{ marginTop: 8 }} onClick={onClose}>ביטול / שיטה אחרת</button>
    </div>
  )
}
