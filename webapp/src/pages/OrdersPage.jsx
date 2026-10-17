import { useEffect, useState } from 'react'
import { fetchUserOrders } from '../api.js'
import { fmtDateTime } from '../utils/time.js'
import PageBanners from '../components/PageBanners.jsx'
import BackButton from '../components/BackButton.jsx'

const STATUS_META = {
  created:   { label: 'ממתין לתשלום', color: '#636366',    icon: '⏳' },
  approved:  { label: 'אושר',          color: '#0066d6', icon: '✅' },
  captured:  { label: 'נגבה',          color: '#006d77', icon: '💳' },
  completed: { label: 'הושלם',         color: '#27692b', icon: '✅' },
  failed:    { label: 'נכשל',          color: '#c53030', icon: '❌' },
  expired:   { label: 'מבוטלת',        color: '#964a08', icon: '🚫' },
  declined:  { label: 'נדחה',          color: '#c53030', icon: '🚫' },
  cancelled:        { label: 'בוטל',              color: '#964a08', icon: '🚫' },
  user_cancelled:   { label: 'בוטל ע״י משתמש',   color: '#964a08', icon: '🚫' },
  admin_approved:   { label: 'אושר ע״י מנהל',  color: '#27692b', icon: '✅' },
  admin_cancelled:  { label: 'בוטל ע״י מנהל',  color: '#964a08', icon: '🚫' },
  pending_delivery: { label: 'ממתין למשלוח',   color: '#964a08', icon: '📦' },
}

function OrderRow({ order }) {
  const [open, setOpen] = useState(false)
  const meta = STATUS_META[order.status] || { label: order.status, color: '#636366', icon: '❓' }
  const isExpired = order.status === 'expired'
  const date = fmtDateTime(order.created_at)

  return (
    <div
      className="card"
      style={{ padding: 0, marginBottom: 10, overflow: 'hidden', borderColor: isExpired ? 'rgba(255,152,0,0.35)' : undefined }}
    >
      <div
        role="button"
        tabIndex={0}
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen(o => !o) } }}
        style={{ padding: '12px 14px', cursor: 'pointer', userSelect: 'none' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--primary)', fontWeight: 700 }}>
            #{order.ref}
          </span>
          <span style={{
            fontSize: 11, fontWeight: 700, color: meta.color, background: `${meta.color}14`,
            borderRadius: 99, padding: '2px 10px',
          }}>
            {meta.icon} {meta.label}
          </span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5, alignItems: 'center' }}>
          <span style={{ fontSize: 13, fontWeight: 600 }}>{order.label}</span>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#27692b' }}>₪{order.amount}</span>
        </div>
        <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 3 }}>{date}</div>
      </div>

      {open && (
        <div style={{
          borderTop: '1px solid var(--border)',
          padding: '10px 14px', fontSize: 12, color: 'var(--hint)',
          lineHeight: 1.8,
        }}>
          {isExpired && (
            <div style={{
              background: 'rgba(255,152,0,0.1)', borderRadius: 8,
              padding: '8px 12px', marginBottom: 8, color: '#964a08', fontSize: 13,
            }}>
              ⚠️ הזמנה לא הושלמה — התשלום לא בוצע בזמן
            </div>
          )}
          <div>מזהה הזמנה: <span style={{ fontFamily: 'monospace' }}>{order.ref}</span></div>
          <div>מוצר: {order.label}</div>
          <div>סכום: ₪{order.amount}</div>
          {order.package_type === 'product' ? (
            <>
              <div>אספקה: {order.delivery_type === 'auto' ? '⚡ מיידית' : '🕐 ידנית'}</div>
              {order.status === 'pending_delivery' && (
                <div style={{
                  background: 'rgba(255,152,0,0.1)', borderRadius: 8,
                  padding: '8px 12px', margin: '8px 0', color: '#964a08', fontSize: 13,
                }}>
                  ⏳ ההזמנה התקבלה ובתהליך עיבוד — תישלח הודעה עם פרטי ההזמנה כשתושלם
                </div>
              )}
              {order.delivery_content && (
                <div style={{
                  background: 'var(--bg)', borderRadius: 8, padding: '8px 12px', margin: '8px 0',
                  fontFamily: 'monospace', fontSize: 12, whiteSpace: 'pre-wrap', wordBreak: 'break-all',
                }}>
                  {order.delivery_content}
                </div>
              )}
            </>
          ) : order.searches === -1
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

export default function OrdersPage({ onBack, onNavigate }) {
  const [orders, setOrders] = useState(null)

  useEffect(() => {
    fetchUserOrders().then(setOrders).catch(() => setOrders([]))
  }, [])

  return (
    <div className="page" style={{ paddingBottom: 24 }}>
      <BackButton onClick={onBack} label="חזרה" />

      <h1 className="page-title">📦 הזמנות שלי</h1>

      <PageBanners page="orders" onNavigate={onNavigate} />

      {orders === null && (
        <div role="status" style={{ textAlign: 'center', color: 'var(--hint)', marginTop: 40 }}>טוען...</div>
      )}

      {orders?.length === 0 && (
        <div style={{ textAlign: 'center', color: 'var(--hint)', marginTop: 40 }}>
          <div style={{ fontSize: 40, marginBottom: 12 }} aria-hidden="true">📭</div>
          <div>אין הזמנות עדיין</div>
        </div>
      )}

      {orders?.map(o => <OrderRow key={o.id} order={o} />)}
    </div>
  )
}
