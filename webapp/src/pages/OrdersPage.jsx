import { useEffect, useState } from 'react'
import { fetchUserOrders } from '../api.js'
import { fmtDateTime } from '../utils/time.js'

const STATUS_META = {
  created:   { label: 'ממתין לתשלום', color: '#888',    icon: '⏳' },
  approved:  { label: 'אושר',          color: '#2196F3', icon: '✅' },
  captured:  { label: 'נגבה',          color: '#00bcd4', icon: '💳' },
  completed: { label: 'הושלם',         color: '#4caf50', icon: '✅' },
  failed:    { label: 'נכשל',          color: '#f44336', icon: '❌' },
  expired:   { label: 'מבוטלת',        color: '#ff9800', icon: '🚫' },
}

function OrderRow({ order }) {
  const [open, setOpen] = useState(false)
  const meta = STATUS_META[order.status] || { label: order.status, color: '#888', icon: '❓' }
  const isExpired = order.status === 'expired'
  const date = fmtDateTime(order.created_at)

  return (
    <div
      style={{
        background: 'var(--bg2)', borderRadius: 12, marginBottom: 8,
        border: `1px solid ${isExpired ? 'rgba(255,152,0,0.2)' : 'rgba(255,255,255,0.06)'}`,
        overflow: 'hidden',
      }}
    >
      <div
        onClick={() => setOpen(o => !o)}
        style={{ padding: '12px 14px', cursor: 'pointer', userSelect: 'none' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--accent, #2196F3)', fontWeight: 700 }}>
            #{order.ref}
          </span>
          <span style={{ fontSize: 11, fontWeight: 700, color: meta.color }}>
            {meta.icon} {meta.label}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5, alignItems: 'center' }}>
          <span style={{ fontSize: 13, fontWeight: 600 }}>{order.label}</span>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#4caf50' }}>₪{order.amount}</span>
        </div>
        <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 3 }}>{date}</div>
      </div>

      {open && (
        <div style={{
          borderTop: '1px solid rgba(255,255,255,0.07)',
          padding: '10px 14px', fontSize: 12, color: 'var(--hint)',
          lineHeight: 1.8,
        }}>
          {isExpired && (
            <div style={{
              background: 'rgba(255,152,0,0.1)', borderRadius: 8,
              padding: '8px 12px', marginBottom: 8, color: '#ff9800', fontSize: 13,
            }}>
              ⚠️ הזמנה לא הושלמה — התשלום לא בוצע בזמן
            </div>
          )}
          <div>מזהה הזמנה: <span style={{ fontFamily: 'monospace' }}>{order.ref}</span></div>
          <div>מוצר: {order.label}</div>
          <div>סכום: ₪{order.amount}</div>
          {order.searches === -1
            ? <div>גישה: ללא הגבלה</div>
            : <div>חיפושים: {order.searches}</div>
          }
          <div>תאריך: {date}</div>
          <div>סטטוס: {meta.icon} {meta.label}</div>
        </div>
      )}
    </div>
  )
}

export default function OrdersPage({ onBack }) {
  const [orders, setOrders] = useState(null)

  useEffect(() => {
    fetchUserOrders().then(setOrders).catch(() => setOrders([]))
  }, [])

  return (
    <div className="page" style={{ paddingBottom: 24 }}>
      <button
        className="btn btn-secondary"
        style={{ marginBottom: 16, width: 'auto', padding: '8px 16px' }}
        onClick={onBack}
      >
        ← חזרה
      </button>

      <div className="page-title">📦 הזמנות שלי</div>

      {orders === null && (
        <div style={{ textAlign: 'center', color: 'var(--hint)', marginTop: 40 }}>טוען...</div>
      )}

      {orders?.length === 0 && (
        <div style={{ textAlign: 'center', color: 'var(--hint)', marginTop: 40 }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📭</div>
          <div>אין הזמנות עדיין</div>
        </div>
      )}

      {orders?.map(o => <OrderRow key={o.id} order={o} />)}
    </div>
  )
}
