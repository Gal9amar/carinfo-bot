import { useState, useEffect } from 'react'
import { fetchGarage, sellFromGarage } from '../api.js'
import LicensePlate from '../components/LicensePlate.jsx'
import BackButton from '../components/BackButton.jsx'

function fmtDate(raw) {
  if (!raw) return null
  try {
    const d = new Date(String(raw).substring(0, 10) + 'T00:00:00')
    return d.toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch { return String(raw).substring(0, 10) }
}

function testStatus(tokefRaw) {
  if (!tokefRaw) return null
  try {
    const tokef = new Date(String(tokefRaw).substring(0, 10) + 'T00:00:00')
    const delta = Math.floor((tokef - new Date()) / (1000 * 60 * 60 * 24))
    if (delta < 0) return `🔴 פג תוקף לפני ${Math.abs(delta)} ימים`
    if (delta <= 30) return `🟡 פג תוקף בעוד ${delta} ימים`
    return `🟢 בתוקף עד ${tokef.toLocaleDateString('he-IL')}`
  } catch { return null }
}

function fmtIls(v) {
  if (v === null || v === undefined || v === '') return '—'
  return `₪${Number(v).toLocaleString('he-IL')}`
}

function GarageCard({ item, onSell }) {
  const [expanded, setExpanded] = useState(false)
  const [selling, setSelling] = useState(false)
  const [salePrice, setSalePrice] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const rec = item.vehicle_data || {}
  const make = rec.tozeret_nm || ''
  const model = rec.kinuy_mishari || rec.degem_nm || ''
  const year = rec.shnat_yitzur || ''
  const color = rec.tzeva_rechev || ''
  const km = rec.kilometer_test_aharon
  const ownership = rec._ownership || []
  const testStr = testStatus(rec.tokef_dt)
  const isSold = item.status === 'sold'
  const profit = isSold ? Number(item.sale_price) - Number(item.purchase_price) : null

  async function handleConfirmSell() {
    const price = parseFloat(salePrice)
    if (!price || price <= 0) return
    setSubmitting(true)
    try {
      await onSell(item.id, price)
      setSelling(false)
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה בשמירת המכירה. נסה שוב.')
    } finally {
      setSubmitting(false)
    }
  }

  const details = [
    ['יצרן', make],
    ['דגם', model],
    ['שנת ייצור', year],
    ['צבע', color],
    ['בעלות נוכחית', rec.baalut],
    ['מספר בעלויות', ownership.length || null],
    ['ק"מ בטסט אחרון', km ? `${Number(km).toLocaleString('he-IL')} ק"מ` : null],
    ['תוקף טסט', testStr],
    ['תאריך רכישה', fmtDate(item.purchase_date)],
    ['ק"מ ברכישה', item.purchase_km ? `${Number(item.purchase_km).toLocaleString('he-IL')} ק"מ` : null],
    ['מחיר רכישה', fmtIls(item.purchase_price)],
    ...(isSold ? [
      ['תאריך מכירה', fmtDate(item.sale_date)],
      ['מחיר מכירה', fmtIls(item.sale_price)],
    ] : []),
  ].filter(([, val]) => val !== null && val !== undefined && val !== '')

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <LicensePlate plate={item.plate} size="sm" />
        <div style={{
          fontSize: 11, fontWeight: 700, borderRadius: 20, padding: '4px 10px', whiteSpace: 'nowrap',
          background: isSold ? '#38a16922' : '#38bdf822',
          color: isSold ? '#38a169' : '#38bdf8',
        }}>{isSold ? '✅ נמכר' : '🚗 במלאי שלי'}</div>
      </div>

      <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 2 }}>
        {[make, model, year].filter(Boolean).join(' · ') || item.plate}
      </div>
      {color && <div style={{ fontSize: 12, color: 'var(--hint)', marginBottom: 10 }}>{color}</div>}

      <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
        <div className="stat-card" style={{ flex: 1, padding: 10 }}>
          <div className="stat-value" style={{ fontSize: 16 }}>{fmtIls(item.purchase_price)}</div>
          <div className="stat-label">מחיר רכישה</div>
        </div>
        {isSold ? (
          <div className="stat-card" style={{ flex: 1, padding: 10 }}>
            <div className="stat-value" style={{ fontSize: 16 }}>{fmtIls(item.sale_price)}</div>
            <div className="stat-label">מחיר מכירה</div>
          </div>
        ) : (
          <div className="stat-card" style={{ flex: 1, padding: 10 }}>
            <div className="stat-value" style={{ fontSize: 16 }}>
              {item.purchase_km ? Number(item.purchase_km).toLocaleString('he-IL') : '—'}
            </div>
            <div className="stat-label">ק"מ ברכישה</div>
          </div>
        )}
      </div>

      {isSold && (
        <div style={{
          textAlign: 'center', padding: '8px 0', borderRadius: 10, marginBottom: 10,
          background: profit >= 0 ? '#38a16922' : '#e53e3e22',
          color: profit >= 0 ? '#38a169' : '#e53e3e',
          fontWeight: 800, fontSize: 15,
        }}>
          {profit >= 0 ? '📈 רווח: ' : '📉 הפסד: '}{fmtIls(Math.abs(profit))}
        </div>
      )}

      {expanded && (
        <div style={{ borderTop: '1px solid var(--bg)', paddingTop: 10, marginTop: 4, marginBottom: 10 }}>
          {details.map(([label, val]) => (
            <div key={label} style={{
              display: 'flex', justifyContent: 'space-between', padding: '6px 0',
              borderBottom: '1px solid var(--bg)', fontSize: 13, gap: 8,
            }}>
              <span style={{ color: 'var(--hint)', flexShrink: 0 }}>{label}</span>
              <span style={{ fontWeight: 600, textAlign: 'end' }}>{String(val)}</span>
            </div>
          ))}
        </div>
      )}

      {selling ? (
        <div>
          <input
            type="number" className="input" placeholder="סכום המכירה (₪)"
            value={salePrice} onChange={e => setSalePrice(e.target.value)}
            style={{ marginBottom: 8 }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn" style={{ flex: 1 }} disabled={submitting || !salePrice} onClick={handleConfirmSell}>
              {submitting ? '...' : 'אישור'}
            </button>
            <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setSelling(false)}>ביטול</button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setExpanded(x => !x)}>
            {expanded ? 'הסתר פרטים' : '🔍 הצג פרטים'}
          </button>
          {!isSold && (
            <button className="btn" style={{ flex: 1 }} onClick={() => setSelling(true)}>💰 מכרתי</button>
          )}
        </div>
      )}
    </div>
  )
}

export default function GaragePage({ onBack }) {
  const [items, setItems] = useState(null)

  useEffect(() => {
    fetchGarage().catch(() => []).then(setItems)
  }, [])

  async function handleSell(id, price) {
    await sellFromGarage(id, price)
    setItems(await fetchGarage().catch(() => items))
  }

  return (
    <div className="page">
      <BackButton onClick={onBack} />
      <div className="page-title">🚘 הרכבים שקניתי</div>

      {items === null && <div className="loading"></div>}

      {items !== null && items.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14 }}>
          עדיין לא סימנת רכבים שקנית.<br />
          חפש רכב ולחץ על "קניתי את הרכב הזה" בדוח המלא כדי להוסיף אותו לכאן.
        </div>
      )}

      {items?.map(item => (
        <GarageCard key={item.id} item={item} onSell={handleSell} />
      ))}
    </div>
  )
}
