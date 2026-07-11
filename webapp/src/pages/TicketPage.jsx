import { useState, useEffect, useRef } from 'react'
import { createTicket, fetchMyTickets, fetchTicket, replyTicket } from '../api.js'
import { fmtDateTime, fmtDate } from '../utils/time.js'
import BackButton from '../components/BackButton.jsx'
import PageBanners from '../components/PageBanners.jsx'

const STATUS_LABEL = { open: 'פתוח', in_progress: 'בטיפול', closed: 'סגור' }
const STATUS_COLOR = { open: '#e07b00', in_progress: '#2481cc', closed: '#38a169' }
const STATUS_ICON  = { open: '🔴', in_progress: '🟡', closed: '🟢' }

export default function TicketPage({ onBack, onNavigate }) {
  const [view, setView] = useState('list') // 'list' | 'create' | 'thread'
  const [tickets, setTickets] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)

  async function loadTickets() {
    setLoading(true)
    try { setTickets(await fetchMyTickets()) } catch {}
    setLoading(false)
  }

  useEffect(() => { loadTickets() }, [])

  if (view === 'create') {
    return (
      <CreateView
        onBack={() => setView('list')}
        onCreated={async (id) => {
          await loadTickets()
          const t = await fetchTicket(id)
          setSelected(t)
          setView('thread')
        }}
      />
    )
  }

  if (view === 'thread' && selected) {
    return (
      <ThreadView
        ticket={selected}
        onBack={async () => { await loadTickets(); setView('list') }}
        onRefresh={async () => {
          const t = await fetchTicket(selected.id)
          setSelected(t)
        }}
      />
    )
  }

  return (
    <div className="page">
      {onBack && <BackButton onClick={onBack} />}
      <div className="page-title">🎫 הפניות שלי</div>

      <PageBanners page="ticket" onNavigate={onNavigate} />

      <button className="btn btn-success" style={{ marginBottom: 16 }} onClick={() => setView('create')}>
        ✉️ פנייה חדשה
      </button>

      {loading && <div className="loading"></div>}

      {!loading && tickets.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14 }}>
          אין פניות פתוחות
        </div>
      )}

      {tickets.map(t => (
        <div
          key={t.id}
          className="card"
          style={{ cursor: 'pointer', borderRight: `3px solid ${STATUS_COLOR[t.status]}`, paddingRight: 12 }}
          onClick={async () => {
            const full = await fetchTicket(t.id)
            setSelected(full)
            setView('thread')
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div className="card-title" style={{ fontSize: 14, flex: 1 }}>{t.subject}</div>
            <span style={{
              fontSize: 11, fontWeight: 700, padding: '3px 10px', borderRadius: 20,
              background: STATUS_COLOR[t.status], color: '#fff',
              whiteSpace: 'nowrap', marginRight: 8, flexShrink: 0,
            }}>
              {STATUS_ICON[t.status]} {STATUS_LABEL[t.status]}
            </span>
          </div>
          <div className="card-subtitle" style={{ marginTop: 4 }}>#{t.id} · {fmtDate(t.created_at)}</div>
        </div>
      ))}
    </div>
  )
}

function CreateView({ onBack, onCreated }) {
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit() {
    if (!subject.trim() || !message.trim()) {
      window.Telegram?.WebApp?.showAlert('נא למלא נושא והודעה')
      return
    }
    setSaving(true)
    try {
      const res = await createTicket(subject.trim(), message.trim())
      await onCreated(res.id)
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה בשליחה, נסה שוב')
    }
    setSaving(false)
  }

  return (
    <div className="page">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--btn)', padding: '0 4px' }}>›</button>
        <div className="page-title" style={{ margin: 0 }}>✉️ פנייה חדשה</div>
      </div>

      <input
        className="input"
        placeholder="נושא הפנייה"
        maxLength={120}
        value={subject}
        onChange={e => setSubject(e.target.value)}
      />
      <textarea
        className="input"
        placeholder="תאר את הבעיה או השאלה..."
        maxLength={2000}
        rows={6}
        value={message}
        onChange={e => setMessage(e.target.value)}
        style={{ resize: 'vertical' }}
      />
      <button className="btn" disabled={saving || !subject.trim() || !message.trim()} onClick={submit}>
        {saving ? '⏳ שולח...' : '📤 שלח פנייה'}
      </button>
      <button className="btn btn-secondary" style={{ marginTop: 8 }} onClick={onBack}>ביטול</button>
    </div>
  )
}

function ThreadView({ ticket, onBack, onRefresh }) {
  const [reply, setReply] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [ticket.replies?.length])

  async function sendReply() {
    if (!reply.trim() || ticket.status === 'closed') return
    setSending(true)
    try {
      await replyTicket(ticket.id, reply.trim())
      setReply('')
      await onRefresh()
    } catch {
      window.Telegram?.WebApp?.showAlert('שגיאה')
    }
    setSending(false)
  }

  const allMessages = [
    { id: 'orig', sender_name: ticket.full_name || 'אתה', is_admin: false, message: ticket.message, created_at: ticket.created_at },
    ...(ticket.replies || []),
  ]

  return (
    <div className="page" style={{ paddingBottom: 80 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <button onClick={onBack} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--btn)', padding: '0 4px' }}>›</button>
        <div className="page-title" style={{ margin: 0, fontSize: 16, flex: 1 }}>{ticket.subject}</div>
      </div>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: STATUS_COLOR[ticket.status] + '18',
        borderRight: `4px solid ${STATUS_COLOR[ticket.status]}`,
        borderRadius: '0 8px 8px 0',
        padding: '8px 12px', marginBottom: 16,
      }}>
        <span style={{ fontSize: 13, color: STATUS_COLOR[ticket.status], fontWeight: 700 }}>
          {STATUS_ICON[ticket.status]} סטטוס: {STATUS_LABEL[ticket.status]}
        </span>
        <span style={{ fontSize: 11, color: 'var(--hint)' }}>#{ticket.id}</span>
      </div>

      {allMessages.map((msg, i) => (
        <div key={msg.id || i} style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: msg.is_admin ? 'flex-start' : 'flex-end',
          marginBottom: 10,
        }}>
          <div style={{
            maxWidth: '85%',
            background: msg.is_admin ? 'var(--bg2)' : 'var(--btn)',
            color: msg.is_admin ? 'var(--text)' : 'var(--btn-text)',
            borderRadius: msg.is_admin ? '4px 16px 16px 16px' : '16px 4px 16px 16px',
            padding: '10px 14px',
            fontSize: 14,
            lineHeight: 1.5,
            wordBreak: 'break-word',
          }}>
            {msg.message}
          </div>
          <div style={{ fontSize: 11, color: 'var(--hint)', marginTop: 3 }}>
            {msg.is_admin ? '🛠 תמיכה' : 'אתה'} · {fmtDateTime(msg.created_at)}
          </div>
        </div>
      ))}

      <div ref={bottomRef} />

      {ticket.status !== 'closed' && (
        <div style={{ position: 'fixed', bottom: 0, right: 0, left: 0, padding: '10px 16px', background: 'var(--bg)', borderTop: '1px solid var(--bg2)' }}>
          <div style={{ display: 'flex', gap: 8, maxWidth: 480, margin: '0 auto' }}>
            <input
              className="input"
              style={{ flex: 1, marginBottom: 0 }}
              placeholder="הוסף תגובה..."
              value={reply}
              onChange={e => setReply(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendReply()}
            />
            <button
              className="btn"
              style={{ width: 'auto', padding: '0 16px', marginTop: 0 }}
              disabled={sending || !reply.trim()}
              onClick={sendReply}
            >
              {sending ? '⏳' : '↑'}
            </button>
          </div>
        </div>
      )}

      {ticket.status === 'closed' && (
        <div style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 13, marginTop: 16 }}>
          הפנייה נסגרה
        </div>
      )}
    </div>
  )
}
