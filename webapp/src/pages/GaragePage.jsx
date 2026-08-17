import { useState, useEffect, useMemo } from 'react'
import { fetchGarage, sellFromGarage, updateGarageItem, deleteGarageItem, fetchMarketPrice } from '../api.js'
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

function netProfit(item) {
  return Number(item.sale_price) - Number(item.purchase_price) - Number(item.expenses || 0)
}

function marketMedian(marketData, year) {
  if (!marketData?.market) return null
  const m = marketData.market
  const yr = year ? parseInt(year) : null
  const filtered = yr && m.items?.length
    ? m.items.filter(i => parseInt(i.vehicleDates?.yearOfProduction || 0) === yr)
    : m.items || []
  const prices = (filtered.length > 0 ? filtered : m.items || []).map(i => i.price).filter(Boolean).sort((a, b) => a - b)
  if (!prices.length) return null
  return prices[Math.floor(prices.length / 2)]
}

function confirmAction(message) {
  return new Promise(resolve => {
    if (window.Telegram?.WebApp?.showConfirm) {
      window.Telegram.WebApp.showConfirm(message, resolve)
    } else {
      resolve(window.confirm(message))
    }
  })
}

function GarageCard({ item, onSell, onUpdate, onDelete }) {
  const [expanded, setExpanded] = useState(false)
  const [selling, setSelling] = useState(false)
  const [salePrice, setSalePrice] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [editing, setEditing] = useState(false)
  const [editPrice, setEditPrice] = useState('')
  const [editKm, setEditKm] = useState('')
  const [editExpenses, setEditExpenses] = useState('')
  const [editSalePrice, setEditSalePrice] = useState('')
  const [editSubmitting, setEditSubmitting] = useState(false)

  const [marketData, setMarketData] = useState(undefined)

  const rec = item.vehicle_data || {}
  const make = rec.tozeret_nm || ''
  const model = rec.kinuy_mishari || rec.degem_nm || ''
  const year = rec.shnat_yitzur || ''
  const color = rec.tzeva_rechev || ''
  const km = rec.kilometer_test_aharon
  const ownership = rec._ownership || []
  const testStr = testStatus(rec.tokef_dt)
  const isSold = item.status === 'sold'
  const profit = isSold ? netProfit(item) : null

  useEffect(() => {
    if (isSold) return
    fetchMarketPrice(item.plate).then(setMarketData).catch(() => setMarketData(null))
  }, [item.plate, isSold])

  async function handleConfirmSell() {
    const price = parseFloat(salePrice)
    if (!price || price <= 0) return
    setSubmitting(true)
    try {
      await onSell(item.id, price)
      setSelling(false)
    } catch (err) {
      window.Telegram?.WebApp?.showAlert(`שגיאה בשמירת המכירה${err?.message ? ` (${err.message})` : ''}. נסה שוב.`)
    } finally {
      setSubmitting(false)
    }
  }

  function openEdit() {
    setEditPrice(String(item.purchase_price ?? ''))
    setEditKm(item.purchase_km != null ? String(item.purchase_km) : '')
    setEditExpenses(item.expenses ? String(item.expenses) : '')
    setEditSalePrice(item.sale_price != null ? String(item.sale_price) : '')
    setEditing(true)
  }

  async function handleSaveEdit() {
    setEditSubmitting(true)
    try {
      await onUpdate(item.id, {
        purchase_price: editPrice !== '' ? parseFloat(editPrice) : null,
        purchase_km: editKm !== '' ? parseInt(editKm, 10) : null,
        expenses: editExpenses !== '' ? parseFloat(editExpenses) : null,
        sale_price: isSold && editSalePrice !== '' ? parseFloat(editSalePrice) : null,
      })
      setEditing(false)
    } catch (err) {
      window.Telegram?.WebApp?.showAlert(`שגיאה בשמירה${err?.message ? ` (${err.message})` : ''}. נסה שוב.`)
    } finally {
      setEditSubmitting(false)
    }
  }

  async function handleDelete() {
    const ok = await confirmAction('למחוק את הרכב הזה מ"רכבים שקניתי"? הפעולה בלתי הפיכה.')
    if (!ok) return
    try {
      await onDelete(item.id)
    } catch (err) {
      window.Telegram?.WebApp?.showAlert(`שגיאה במחיקה${err?.message ? ` (${err.message})` : ''}. נסה שוב.`)
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
    ['הוצאות נוספות', item.expenses ? fmtIls(item.expenses) : null],
    ...(isSold ? [
      ['תאריך מכירה', fmtDate(item.sale_date)],
      ['מחיר מכירה', fmtIls(item.sale_price)],
      ['רווח/הפסד נטו', fmtIls(profit)],
    ] : []),
  ].filter(([, val]) => val !== null && val !== undefined && val !== '')

  const median = !isSold ? marketMedian(marketData, year) : null
  const marketAuthorized = marketData?.authorized !== false
  const unrealized = median != null ? median - Number(item.purchase_price) - Number(item.expenses || 0) : null

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

      {!isSold && median != null && (
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '8px 10px', borderRadius: 10, marginBottom: 10,
          background: 'var(--bg)', fontSize: 12,
        }}>
          <span style={{ color: 'var(--hint)' }}>📊 שווי שוק משוער (לא ממומש)</span>
          <span style={{
            fontWeight: 700,
            ...(marketAuthorized ? {} : { filter: 'blur(4px)', userSelect: 'none' }),
          }}>
            {fmtIls(median)} ({unrealized >= 0 ? '+' : ''}{fmtIls(unrealized)})
          </span>
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

      {editing ? (
        <div>
          <input type="number" className="input" placeholder="מחיר רכישה (₪)"
            value={editPrice} onChange={e => setEditPrice(e.target.value)} style={{ marginBottom: 8 }} />
          <input type="number" className="input" placeholder='ק"מ ברכישה'
            value={editKm} onChange={e => setEditKm(e.target.value)} style={{ marginBottom: 8 }} />
          <input type="number" className="input" placeholder="הוצאות נוספות (₪)"
            value={editExpenses} onChange={e => setEditExpenses(e.target.value)} style={{ marginBottom: 8 }} />
          {isSold && (
            <input type="number" className="input" placeholder="מחיר מכירה (₪)"
              value={editSalePrice} onChange={e => setEditSalePrice(e.target.value)} style={{ marginBottom: 8 }} />
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn" style={{ flex: 1 }} disabled={editSubmitting} onClick={handleSaveEdit}>
              {editSubmitting ? '...' : 'שמור שינויים'}
            </button>
            <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setEditing(false)}>ביטול</button>
          </div>
        </div>
      ) : selling ? (
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
        <>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <button className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setExpanded(x => !x)}>
              {expanded ? 'הסתר פרטים' : '🔍 הצג פרטים'}
            </button>
            {!isSold && (
              <button className="btn" style={{ flex: 1 }} onClick={() => setSelling(true)}>💰 מכרתי</button>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-secondary" style={{ flex: 1, fontSize: 12 }} onClick={openEdit}>✏️ ערוך</button>
            <button className="btn btn-secondary" style={{ flex: 1, fontSize: 12, color: '#e53e3e' }} onClick={handleDelete}>🗑️ מחק</button>
          </div>
        </>
      )}
    </div>
  )
}

export default function GaragePage({ onBack }) {
  const [items, setItems] = useState(null)
  const [filter, setFilter] = useState('all') // all | owned | sold
  const [sort, setSort] = useState('date') // date | profit

  useEffect(() => {
    fetchGarage().catch(() => []).then(setItems)
  }, [])

  async function refresh() {
    setItems(await fetchGarage().catch(() => items))
  }

  async function handleSell(id, price) {
    await sellFromGarage(id, price)
    await refresh()
  }

  async function handleUpdate(id, data) {
    await updateGarageItem(id, data)
    await refresh()
  }

  async function handleDelete(id) {
    await deleteGarageItem(id)
    await refresh()
  }

  const summary = useMemo(() => {
    const owned = items?.filter(i => i.status === 'owned') ?? []
    const sold = items?.filter(i => i.status === 'sold') ?? []
    const invested = owned.reduce((s, i) => s + Number(i.purchase_price) + Number(i.expenses || 0), 0)
    const realized = sold.reduce((s, i) => s + netProfit(i), 0)
    return { ownedCount: owned.length, soldCount: sold.length, invested, realized }
  }, [items])

  const visible = useMemo(() => {
    let list = items ?? []
    if (filter === 'owned') list = list.filter(i => i.status === 'owned')
    if (filter === 'sold') list = list.filter(i => i.status === 'sold')
    if (sort === 'profit') {
      list = [...list].sort((a, b) => {
        const pa = a.status === 'sold' ? netProfit(a) : -Infinity
        const pb = b.status === 'sold' ? netProfit(b) : -Infinity
        return pb - pa
      })
    }
    return list
  }, [items, filter, sort])

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

      {items !== null && items.length > 0 && (
        <>
          {/* ── Summary ── */}
          <div className="card" style={{ marginBottom: 14 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div className="stat-card">
                <div className="stat-value" style={{ fontSize: 18 }}>{summary.ownedCount}</div>
                <div className="stat-label">רכבים במלאי</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ fontSize: 18 }}>{summary.soldCount}</div>
                <div className="stat-label">רכבים שנמכרו</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ fontSize: 16 }}>{fmtIls(summary.invested)}</div>
                <div className="stat-label">הון מושקע (במלאי)</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{
                  fontSize: 16, color: summary.realized >= 0 ? '#38a169' : '#e53e3e',
                }}>{summary.realized >= 0 ? '+' : ''}{fmtIls(summary.realized)}</div>
                <div className="stat-label">רווח/הפסד ממומש</div>
              </div>
            </div>
          </div>

          {/* ── Filter / sort ── */}
          <div style={{ display: 'flex', gap: 6, marginBottom: 14, background: 'var(--bg2)', borderRadius: 14, padding: 4 }}>
            {[
              { id: 'all', label: 'הכל' },
              { id: 'owned', label: 'במלאי' },
              { id: 'sold', label: 'נמכרו' },
            ].map(f => (
              <button key={f.id} onClick={() => setFilter(f.id)} style={{
                flex: 1, padding: '8px 0', border: 'none', borderRadius: 11,
                fontSize: 13, fontWeight: 600, cursor: 'pointer',
                background: filter === f.id ? 'linear-gradient(135deg,#1e40af,#0ea5e9)' : 'transparent',
                color: filter === f.id ? '#fff' : 'var(--hint)',
              }}>{f.label}</button>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
            {[
              { id: 'date', label: '🕒 החדש ביותר' },
              { id: 'profit', label: '💰 לפי רווח' },
            ].map(s => (
              <button key={s.id} onClick={() => setSort(s.id)} style={{
                flex: 1, padding: '7px 0', borderRadius: 10,
                fontSize: 12, fontWeight: 600, cursor: 'pointer',
                border: `1px solid ${sort === s.id ? '#38bdf8' : 'var(--bg2)'}`,
                background: sort === s.id ? '#38bdf822' : 'var(--bg2)',
                color: sort === s.id ? '#38bdf8' : 'var(--hint)',
              }}>{s.label}</button>
            ))}
          </div>

          {visible.length === 0 && (
            <div className="card" style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14 }}>
              אין רכבים בסינון הזה
            </div>
          )}

          {visible.map(item => (
            <GarageCard key={item.id} item={item} onSell={handleSell} onUpdate={handleUpdate} onDelete={handleDelete} />
          ))}
        </>
      )}
    </div>
  )
}
