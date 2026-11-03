import { useState, useEffect } from 'react'
import PremiumLock from './PremiumLock.jsx'
import PremiumHeader from './PremiumHeader.jsx'
import {
  fetchVehicleLevi, fetchLeviOwners, calcVehicleLevi,
  adminLeviSendSms as leviSendSms, adminLeviValidate as leviValidate, adminLeviLogout as leviLogout,
} from '../api.js'

const ROW = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
  padding: '6px 0', borderBottom: '1px solid rgba(0,100,200,0.1)', fontSize: 14, gap: 8,
}
const INPUT = {
  width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid var(--border)',
  background: 'var(--bg)', color: 'var(--text-main)', fontSize: 15, boxSizing: 'border-box',
}
const BTN = (primary = true, busy = false) => ({
  padding: '10px 16px', borderRadius: 10, fontWeight: 700, fontSize: 14, cursor: busy ? 'default' : 'pointer',
  opacity: busy ? 0.6 : 1, border: primary ? 'none' : '1px solid var(--border)',
  background: primary ? 'var(--btn)' : 'var(--bg)', color: primary ? 'var(--btn-text)' : 'var(--text-main)',
})

function Row({ label, value, strong }) {
  if (value === null || value === undefined || value === '') return null
  // Long text (e.g. the Levi-vs-Yad2 comparison) goes on its own line instead of wrapping in a narrow column.
  const stack = typeof value === 'string' && value.length > 22
  return (
    <div style={stack ? { ...ROW, flexDirection: 'column', gap: 4 } : ROW}>
      <span style={{ color: 'var(--hint)', flexShrink: 0, minWidth: stack ? 0 : 110 }}>{label}</span>
      <span style={{ fontWeight: strong ? 800 : 500, textAlign: stack ? 'start' : 'end' }}>{value}</span>
    </div>
  )
}

const shekel = (n) => `₪${Math.round(Number(n)).toLocaleString()}`

export default function LeviCard({ plate, user, onNavigate }) {
  const entitled = !!user?.show_levi
  const [phase, setPhase] = useState('loading') // loading | login | code | result | error
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [phoneMask, setPhoneMask] = useState('')
  // price adjustment
  const [calcOpen, setCalcOpen] = useState(false)
  const [owners, setOwners] = useState([])
  const [km, setKm] = useState('')
  const [hands, setHands] = useState(1)
  const [picked, setPicked] = useState([''])
  const [calc, setCalc] = useState(null)

  function load() {
    setPhase('loading'); setErr(''); setCalc(null)
    fetchVehicleLevi(plate)
      .then(d => { setData(d); setPhase('result') })
      .catch(e => {
        if (e.authExpired) { setPhase('login'); return }
        setErr(e.message || 'שגיאה'); setPhase('error')
      })
  }
  useEffect(() => { if (entitled && plate) load() }, [plate, entitled])   // eslint-disable-line react-hooks/exhaustive-deps

  async function run(fn) {
    setBusy(true); setErr('')
    try { await fn() } catch (e) {
      if (e.authExpired) setPhase('login')
      setErr(e.message || 'שגיאה')
    } finally { setBusy(false) }
  }

  const sendSms = () => run(async () => { const r = await leviSendSms(phone); setPhoneMask(r.phone); setCode(''); setPhase('code') })
  const validate = () => run(async () => { await leviValidate(code); load() })
  const logout = () => run(async () => { await leviLogout(); setData(null); setPhone(''); setPhase('login') })

  function openCalc() {
    setCalcOpen(o => !o)
    if (!owners.length) {
      fetchLeviOwners().then(r => {
        setOwners(r.owners || [])
        setPicked(p => p.map(v => v || (r.owners?.[0]?.id ?? '')))
      }).catch(e => { if (e.authExpired) setPhase('login'); setErr(e.message || 'שגיאה') })
    }
  }
  function setHandCount(n) {
    const next = Math.max(1, Math.min(8, n))
    setHands(next)
    setPicked(p => Array.from({ length: next }, (_, i) => p[i] || owners[0]?.id || ''))
  }
  const doCalc = () => run(async () => {
    const kmNum = parseInt(String(km).replace(/\D/g, ''), 10)
    if (!Number.isFinite(kmNum)) throw new Error('הזן קילומטראז׳ תקין')
    if (picked.some(v => !v)) throw new Error('בחר סוג בעלות לכל יד')
    setCalc(await calcVehicleLevi(plate, kmNum, picked))
  })

  // ── Not entitled: locked teaser (only rendered when the feature is open to someone) ──
  if (!entitled) {
    if (!user?.levi_teaser) return null
    return (
      <PremiumLock locked title="מחירון לוי יצחק" publicLabel={user?.levi_public_label} onNavigate={onNavigate}>
        <div className="card" style={{ margin: 0 }}>
          <PremiumHeader title="📗 מחירון לוי יצחק" />
          <Row label="מחיר מחירון (בסיס)" value="₪63,000" />
          <Row label="מחירון מול יד2" value="נמוך ב־8% מחציון המודעות" />
        </div>
      </PremiumLock>
    )
  }

  const s = data?.summary

  return (
    <div className="card" style={{ marginBottom: 12 }} role="group" aria-label="מחירון לוי יצחק">
      <PremiumHeader title="📗 מחירון לוי יצחק" publicLabel={user?.levi_public_label} />

      {phase === 'loading' && <div style={{ display: 'flex', justifyContent: 'center', padding: 12 }}><div className="loading"></div></div>}

      {phase === 'login' && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: 13, color: 'var(--hint)', lineHeight: 1.6 }}>
            כדי לראות את מחיר המחירון צריך להזדהות מול לוי יצחק, כמו באפליקציה שלהם: מספר נייד, ואז קוד בן 6 ספרות ב־SMS.
            המספר נשלח ללוי יצחק לצורך האימות; אצלנו נשמרים רק המספר ואסימון הגישה, ואפשר להתנתק בכל רגע.
          </div>
          <input style={INPUT} inputMode="tel" dir="ltr" placeholder="05XXXXXXXX" value={phone} onChange={e => setPhone(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !busy && phone.trim() && sendSms()} />
          <button style={BTN(true, busy)} disabled={busy || !phone.trim()} onClick={sendSms}>{busy ? 'שולח…' : '🔑 שלח קוד SMS'}</button>
        </div>
      )}

      {phase === 'code' && (
        <div style={{ display: 'grid', gap: 10 }}>
          <div style={{ fontSize: 13, color: 'var(--hint)' }}>קוד אימות נשלח אל <b dir="ltr">{phoneMask}</b>:</div>
          <input style={{ ...INPUT, letterSpacing: 6, textAlign: 'center' }} inputMode="numeric" dir="ltr" maxLength={6} placeholder="••••••"
            value={code} autoFocus onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
            onKeyDown={e => e.key === 'Enter' && !busy && code.length === 6 && validate()} />
          <div style={{ display: 'flex', gap: 8 }}>
            <button style={{ ...BTN(true, busy), flex: 1 }} disabled={busy || code.length !== 6} onClick={validate}>{busy ? 'מאמת…' : 'אמת והתחבר'}</button>
            <button style={BTN(false, busy)} disabled={busy} onClick={() => { setPhase('login'); setErr('') }}>שינוי מספר</button>
          </div>
        </div>
      )}

      {phase === 'error' && (
        <div style={{ display: 'grid', gap: 8 }}>
          <div style={{ fontSize: 13, color: '#c53030' }}>⚠️ {err}</div>
          <button style={BTN(false)} onClick={load}>🔄 נסה שוב</button>
        </div>
      )}

      {phase === 'result' && s && (
        <>
          <Row label="מחיר מחירון (בסיס)" value={s.price ? <span dir="ltr">{shekel(s.price)}</span> : 'לא נמצא מחיר'} strong />
          {data.comparison_text ? <Row label="מחירון מול יד2" value={data.comparison_text} /> : null}
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>מחיר בסיס, לפני התאמה לק״מ, ידיים וסוג בעלות. הערכה בלבד.</div>

          <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
            <button style={BTN(true)} onClick={openCalc}>⚖️ שקלול מחיר</button>
            <button style={BTN(false, busy)} disabled={busy} onClick={logout}>התנתק מלוי יצחק</button>
          </div>

          {calcOpen && (
            <div style={{ display: 'grid', gap: 10, marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
              <div>
                <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 4 }}>קילומטראז׳</div>
                <input style={INPUT} inputMode="numeric" dir="ltr" placeholder="85000" value={km} onChange={e => setKm(e.target.value)} />
              </div>
              <div>
                <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 4 }}>מספר ידיים (כולל הבעלים הנוכחי)</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <button style={BTN(false)} onClick={() => setHandCount(hands - 1)} disabled={hands <= 1} aria-label="הפחתת ידיים">−</button>
                  <b style={{ minWidth: 20, textAlign: 'center' }}>{hands}</b>
                  <button style={BTN(false)} onClick={() => setHandCount(hands + 1)} disabled={hands >= 8} aria-label="הוספת ידיים">+</button>
                </div>
              </div>
              {picked.map((v, i) => (
                <div key={i}>
                  <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 4 }}>יד {i + 1}{i === hands - 1 ? ' (הבעלות הנוכחית)' : ''} — סוג בעלות</div>
                  <select style={INPUT} value={v} onChange={e => setPicked(p => p.map((x, j) => j === i ? e.target.value : x))}>
                    {owners.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
                  </select>
                </div>
              ))}
              <button style={BTN(true, busy)} disabled={busy || !owners.length} onClick={doCalc}>{busy ? 'מחשב…' : 'חשב מחיר מותאם'}</button>
              {calc && (
                <div style={{ background: 'var(--bg)', borderRadius: 12, padding: 12, display: 'grid', gap: 4 }}>
                  <div style={{ fontWeight: 800, fontSize: 16 }}>
                    💰 מחיר מותאם: {calc.price ? <span dir="ltr">{shekel(calc.price)}</span> : 'לא התקבל מחיר'}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--hint)' }}>{Number(calc.km).toLocaleString()} ק״מ · {calc.owner_names?.length} ידיים ({calc.owner_names?.join(', ')})</div>
                  {calc.comparison_text ? <div style={{ fontSize: 13 }}>⚖️ מחירון מול יד2: {calc.comparison_text}</div> : null}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {err && phase !== 'error' ? <div style={{ color: '#c53030', fontSize: 13, marginTop: 8 }}>⚠️ {err}</div> : null}
    </div>
  )
}
