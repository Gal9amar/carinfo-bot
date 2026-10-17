import { useState, useRef } from 'react'
import { fetchCompare } from '../api.js'
import { formatPlateInput } from '../utils/plate.js'

const ERROR_TEXT = {
  NOT_FOUND: 'לא נמצא רכב עם המספר הזה',
  SAME_PLATE: 'יש להזין מספר רכב שונה מהרכב שמוצג בדוח',
  QUOTA_EXCEEDED: 'נגמרו החיפושים שלך — רכוש חבילה כדי להמשיך להשוות',
  MAINTENANCE: 'השירות בתחזוקה כרגע — נסה שוב בעוד רגע',
  REGISTRY_UNAVAILABLE: 'מאגר הרכבים אינו זמין כרגע. נסה שוב בעוד רגע',
  NETWORK_ERROR: 'בעיית חיבור לאינטרנט. בדוק את החיבור ונסה שוב',
  SERVER_ERROR: 'אירעה שגיאה בהשוואה. נסה שוב בעוד רגע',
  BAD_REQUEST: 'מספר הרכב אינו תקין',
}

function Header() {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontWeight: 700, fontSize: 15 }}>
        <span aria-hidden="true">⚖️ </span>השוואה בין רכבים
      </div>
    </div>
  )
}

const cellBase = { padding: '8px 10px', fontSize: 13, textAlign: 'start', verticalAlign: 'top', borderBottom: '1px solid rgba(0,100,200,0.1)' }

function CompareTable({ data }) {
  const rows = Array.isArray(data?.rows) ? data.rows : []
  const a = data?.a || {}
  const b = data?.b || {}
  const show = v => (v === null || v === undefined || v === '' ? '—' : String(v))
  return (
    <div style={{ overflowX: 'auto', marginTop: 12 }} tabIndex={0} role="region" aria-label="טבלת השוואה">
      <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
        <caption className="sr-only">השוואה בין הרכב {show(a.title)} לרכב {show(b.title)}</caption>
        <colgroup><col style={{ width: '27%' }} /><col style={{ width: '36.5%' }} /><col style={{ width: '36.5%' }} /></colgroup>
        <thead>
          <tr>
            <th scope="col" style={{ ...cellBase, fontSize: 12, color: 'var(--hint)', background: 'var(--bg)', borderBottom: '2px solid rgba(0,100,200,0.18)' }}>נתון</th>
            {[a, b].map((v, i) => (
              <th key={i} scope="col" style={{ ...cellBase, fontWeight: 700, background: 'var(--bg)', borderBottom: '2px solid rgba(0,100,200,0.18)' }}>
                <div>{show(v.title)}</div>
                <div dir="ltr" style={{ fontSize: 12, color: 'var(--hint)', fontWeight: 500, textAlign: 'right' }}>{show(v.plate)}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const diff = show(r?.a) !== show(r?.b)
            const cell = {
              ...cellBase,
              unicodeBidi: 'plaintext',
              ...(diff ? { fontWeight: 700, background: 'rgba(0,102,214,0.08)' } : {}),
            }
            return (
              <tr key={i}>
                <th scope="row" style={{ ...cellBase, fontSize: 12, fontWeight: 600, color: 'var(--hint)' }}>
                  {show(r?.label)}
                  {diff && <span aria-hidden="true" style={{ marginInlineStart: 4 }}>≠</span>}
                  {diff && <span className="sr-only"> (שונה)</span>}
                </th>
                <td style={cell}>{show(r?.a)}</td>
                <td style={cell}>{show(r?.b)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function CompareCard({ plate, user, onNavigate }) {
  const [input, setInput] = useState('')
  const [state, setState] = useState('idle') // idle | loading | done | error
  const [errCode, setErrCode] = useState('')
  const [data, setData] = useState(null)
  const inputRef = useRef(null)

  const digits = input.replace(/\D/g, '')
  const unlimited = user?.searches_left === -1
  const canSubmit = digits.length >= 5 && state !== 'loading'

  async function submit(e) {
    e.preventDefault()
    if (!canSubmit) return
    if (digits === String(plate || '').replace(/\D/g, '')) {
      setErrCode('SAME_PLATE'); setState('error'); return
    }
    setState('loading'); setErrCode('')
    try {
      const res = await fetchCompare(String(plate).replace(/\D/g, ''), digits)
      setData(res)
      setState('done')
    } catch (err) {
      const code = err?.message || 'SERVER_ERROR'
      setErrCode(code in ERROR_TEXT ? code : 'SERVER_ERROR')
      setState('error')
    }
  }

  const inputId = 'compare-plate-input'
  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <Header />
      <form onSubmit={submit} noValidate>
        <label htmlFor={inputId} style={{ display: 'block', fontSize: 13, color: 'var(--hint)', marginBottom: 6, fontWeight: 600 }}>
          מספר רישוי של הרכב להשוואה
        </label>
        <div style={{ display: 'flex', gap: 8, alignItems: 'stretch' }}>
          <input
            id={inputId} ref={inputRef} type="tel" inputMode="numeric" dir="ltr"
            className="input" placeholder="12-345-67" maxLength={10}
            autoComplete="off"
            aria-describedby="compare-quota-note"
            value={input}
            onChange={e => setInput(formatPlateInput(e.target.value))}
            style={{ flex: 1, minWidth: 0, margin: 0, textAlign: 'center', fontSize: 18, letterSpacing: 2, fontWeight: 700 }}
          />
          <button type="submit" className="btn" disabled={!canSubmit}
            style={{ margin: 0, width: 'auto', minWidth: 96, minHeight: 44 }}>
            {state === 'loading' ? '⏳ משווה...' : 'השווה'}
          </button>
        </div>
        <div id="compare-quota-note" style={{ fontSize: 12, color: 'var(--hint)', marginTop: 8 }}>
          {unlimited ? 'המנוי שלך כולל השוואות ללא הגבלה' : 'ההשוואה צורכת חיפוש אחד'}
        </div>
      </form>

      <div role="status" aria-live="polite" style={state === 'done' ? { marginTop: 10, fontSize: 13, fontWeight: 600 } : undefined}
        className={state === 'done' ? undefined : 'sr-only'}>
        {state === 'loading' && 'משווה בין הרכבים...'}
        {state === 'done' && `ההשוואה מוכנה: ${data?.a?.title || plate} מול ${data?.b?.title || digits}`}
      </div>

      {state === 'error' && (
        <div role="alert" style={{
          marginTop: 10, padding: '10px 12px', borderRadius: 10, fontSize: 13,
          background: 'rgba(197,48,48,0.08)', color: '#c53030', fontWeight: 600,
        }}>
          <span aria-hidden="true">❌ </span>{ERROR_TEXT[errCode] || ERROR_TEXT.SERVER_ERROR}
          {errCode === 'QUOTA_EXCEEDED' && onNavigate && (
            <button type="button" className="btn" style={{ width: '100%', marginTop: 10, minHeight: 44 }}
              onClick={() => onNavigate('packages')}>לחבילות</button>
          )}
        </div>
      )}

      {state === 'done' && data && <CompareTable data={data} />}
    </div>
  )
}
