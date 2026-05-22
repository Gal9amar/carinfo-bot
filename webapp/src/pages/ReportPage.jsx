import { useState, useEffect } from 'react'
import { fetchVehicle } from '../api.js'

const FIELDS = [
  { section: '🚗 פרטים כלליים', items: [
    { key: 'tozeret_nm',       label: 'יצרן' },
    { key: 'kinuy_mishari',    label: 'שם מסחרי' },
    { key: 'degem_nm',         label: 'דגם' },
    { key: 'shnat_yitzur',     label: 'שנת ייצור' },
    { key: 'tzeva_rechev',     label: 'צבע' },
    { key: 'mispar_dlatot',    label: 'דלתות' },
    { key: 'sug_rechev_nm',    label: 'סוג רכב' },
  ]},
  { section: '⚙️ מפרט טכני', items: [
    { key: 'sug_delek_nm',     label: 'סוג דלק' },
    { key: 'nefah_manoa',      label: 'נפח מנוע (סמ"ק)' },
    { key: 'koah_sus',         label: 'כוח סוס' },
    { key: 'sug_hanaa_nm',     label: 'סוג הנעה' },
    { key: 'mispar_halachim',  label: "מס' הילוכים" },
    { key: 'kvuzat_zihum_nm',  label: 'קבוצת זיהום' },
    { key: 'zmig_kidmi',       label: 'צמיג קדמי' },
    { key: 'zmig_ahori',       label: 'צמיג אחורי' },
  ]},
  { section: '📅 היסטוריה', items: [
    { key: 'moed_aliya_lakvish',  label: 'עלייה לכביש' },
    { key: 'tokef_dt',            label: 'תוקף רישיון' },
    { key: 'mivchan_acharon_dt',  label: 'טסט אחרון' },
    { key: 'km_aharon_bmivhan',   label: 'ק"מ בטסט' },
    { key: 'mispar_baalim',       label: "מס' בעלים" },
    { key: 'baalut_nm',           label: 'בעלות נוכחית' },
  ]},
  { section: '🛡️ בטיחות', items: [
    { key: 'abs',               label: 'ABS' },
    { key: 'esp',               label: 'ESP' },
    { key: 'mispar_kariot_avir',label: 'כריות אוויר' },
    { key: 'plitat_co2',        label: 'פליטת CO₂' },
  ]},
]

function val(record, key) {
  const v = record[key]
  if (v === null || v === undefined || v === '') return null
  return String(v)
}

export default function ReportPage({ plate }) {
  const [record, setRecord] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!plate) { setError('לא צוין מספר רכב'); return }
    fetchVehicle(plate)
      .then(setRecord)
      .catch(() => setError('הרכב לא נמצא או שגיאה בטעינה'))
  }, [plate])

  if (error) {
    return (
      <div className="page">
        <div className="loading">❌ {error}</div>
        <button className="btn btn-secondary" style={{marginTop:16}} onClick={() => window.Telegram?.WebApp?.close()}>סגור</button>
      </div>
    )
  }

  if (!record) {
    return <div className="loading">🔍 טוען נתוני רכב...</div>
  }

  const plateNum = record.mispar_rechev || plate
  const make  = record.tozeret_nm || ''
  const model = record.kinuy_mishari || record.degem_nm || ''
  const year  = record.shnat_yitzur || ''

  return (
    <div className="page">
      <div style={{ textAlign: 'center', marginBottom: 20 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 4 }}>דוח רכב</div>
        <div style={{
          display: 'inline-block',
          background: 'var(--btn)',
          color: 'var(--btn-text)',
          fontWeight: 800,
          fontSize: 22,
          padding: '8px 24px',
          borderRadius: 10,
          letterSpacing: 2,
          marginBottom: 8,
        }}>{plateNum}</div>
        <div style={{ fontSize: 16, fontWeight: 600, marginTop: 6 }}>
          {[make, model, year].filter(Boolean).join(' · ')}
        </div>
      </div>

      {FIELDS.map(({ section, items }) => {
        const visible = items.filter(({ key }) => val(record, key) !== null)
        if (!visible.length) return null
        return (
          <div key={section} className="card" style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10 }}>{section}</div>
            {visible.map(({ key, label }) => (
              <div key={key} style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '6px 0',
                borderBottom: '1px solid var(--bg)',
                fontSize: 14,
              }}>
                <span style={{ color: 'var(--hint)' }}>{label}</span>
                <span style={{ fontWeight: 500 }}>{val(record, key)}</span>
              </div>
            ))}
          </div>
        )
      })}

      <button
        className="btn btn-secondary"
        style={{ marginTop: 8 }}
        onClick={() => window.Telegram?.WebApp?.close()}
      >
        סגור
      </button>
    </div>
  )
}
