import { useState, useEffect } from 'react'
import PremiumLock from './PremiumLock.jsx'
import PremiumHeader from './PremiumHeader.jsx'
import { fetchVehicleInsurance } from '../api.js'

const ROW = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
  padding: '6px 0', borderBottom: '1px solid rgba(0,100,200,0.1)', fontSize: 14, gap: 8,
}

export default function InsuranceCard({ plate, user, onNavigate }) {
  const entitled = !!user?.show_insurance
  const [state, setState] = useState('loading') // loading | done | error
  const [data, setData] = useState(null)
  const [err, setErr] = useState('')

  function load() {
    setState('loading'); setErr('')
    fetchVehicleInsurance(plate)
      .then(d => { setData(d); setState('done') })
      .catch(e => { setErr(e.message || 'בדיקת הביטוח לא זמינה כרגע'); setState('error') })
  }
  useEffect(() => { if (entitled && plate) load() }, [plate, entitled])   // eslint-disable-line react-hooks/exhaustive-deps

  if (!entitled) {
    if (!user?.insurance_teaser) return null
    return (
      <PremiumLock locked title="חברת ביטוח רשומה" publicLabel={user?.insurance_public_label} onNavigate={onNavigate}>
        <div className="card" style={{ margin: 0 }}>
          <PremiumHeader title="🛡 חברת ביטוח רשומה" />
          <div style={ROW}><span style={{ color: 'var(--hint)' }}>ביטוח צד ג׳ / מקיף</span><span style={{ fontWeight: 700 }}>ליברה</span></div>
        </div>
      </PremiumLock>
    )
  }

  const pending = data ? [...(data.failed || []), ...(data.manual || [])] : []

  return (
    <div className="card" style={{ marginBottom: 12 }} role="group" aria-label="חברת ביטוח רשומה">
      <PremiumHeader title="🛡 חברת ביטוח רשומה" publicLabel={user?.insurance_public_label} />

      {state === 'loading' && <div style={{ display: 'flex', justifyContent: 'center', padding: 12 }}><div className="loading"></div></div>}

      {state === 'error' && (
        <div style={{ display: 'grid', gap: 8 }}>
          <div style={{ fontSize: 13, color: '#c53030' }}>⚠️ {err}</div>
          <button className="btn" style={{ width: 'auto', padding: '0 16px', minHeight: 40 }} onClick={load}>🔄 נסה שוב</button>
        </div>
      )}

      {state === 'done' && data && (
        <>
          {data.insured?.length ? (
            <div style={ROW}>
              <span style={{ color: 'var(--hint)', flexShrink: 0, minWidth: 110 }}>ביטוח צד ג׳ / מקיף</span>
              <span style={{ fontWeight: 800, textAlign: 'end', color: '#177a33' }}>✅ {data.insured.join(', ')}</span>
            </div>
          ) : (
            // long message: its own line under the label instead of wrapping inside a narrow column
            <div style={{ ...ROW, flexDirection: 'column', gap: 4 }}>
              <span style={{ color: 'var(--hint)' }}>ביטוח צד ג׳ / מקיף</span>
              <span style={{ fontWeight: 800 }}>לא נמצאה פוליסה ({data.no?.length || 0} חברות נבדקו)</span>
            </div>
          )}
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
            נכון ל־{data.date}, לפי אתרי חברות הביטוח — לא אישור משפטי. “לא נמצאה פוליסה” אצל חברה אחת אינו אומר שהרכב לא מבוטח.
          </div>
          {pending.length > 0 && (
            <details style={{ marginTop: 10 }}>
              <summary style={{ cursor: 'pointer', fontSize: 13, fontWeight: 700 }}>🛡 בדיקה ידנית בחברות נוספות ({pending.length})</summary>
              <div style={{ display: 'grid', gap: 6, marginTop: 8 }}>
                {pending.map(p => (
                  <a key={p.name} href={p.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: 'var(--link, #0066d6)' }}>• {p.name} ↗</a>
                ))}
              </div>
            </details>
          )}
        </>
      )}
    </div>
  )
}
