import { useState, useEffect } from 'react'
import { fetchReferral } from '../api.js'

export default function ReferralPage({ onBack }) {
  const [data, setData] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => { fetchReferral().then(setData).catch(() => {}) }, [])

  function copyLink() {
    if (!data?.link) return
    navigator.clipboard?.writeText(data.link).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function shareLink() {
    if (!data?.link) return
    const text = encodeURIComponent('הצטרף לבוט הבדיקת הרכבים הכי טוב בישראל! 🚗')
    const url  = encodeURIComponent(data.link)
    const shareUrl = `https://t.me/share/url?url=${url}&text=${text}`
    window.Telegram?.WebApp?.openTelegramLink?.(shareUrl)
  }

  return (
    <div className="page">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        {onBack && (
          <button onClick={onBack} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: 'var(--btn)', padding: '0 4px' }}>›</button>
        )}
        <div className="page-title" style={{ margin: 0 }}>🤝 הפנה חבר</div>
      </div>

      {/* Hero */}
      <div style={{
        background: 'linear-gradient(135deg,#2481cc,#1a5fa8)',
        borderRadius: 16, padding: '20px 16px', marginBottom: 16, textAlign: 'center', color: '#fff',
      }}>
        <div style={{ fontSize: 40, marginBottom: 8 }}>🎁</div>
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>הפנה חברים וקבל חיפושים</div>
        <div style={{ fontSize: 14, opacity: 0.9 }}>
          על כל חבר שמצטרף דרך הלינק שלך<br />
          תקבל <strong>{data?.bonus ?? 10} חיפושים</strong> בונוס
        </div>
      </div>

      {/* Stats */}
      {data && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
          <div className="stat-card">
            <div className="stat-value">{data.count}</div>
            <div className="stat-label">חברים הופנו</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{data.total_earned}</div>
            <div className="stat-label">חיפושים הרווחת</div>
          </div>
        </div>
      )}

      {/* Link */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8 }}>הלינק האישי שלך:</div>
        <div style={{
          background: 'var(--bg2)', borderRadius: 10, padding: '10px 12px',
          fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-all',
          color: 'var(--text)', marginBottom: 10, direction: 'ltr', textAlign: 'left',
        }}>
          {data?.link ?? '⏳ טוען...'}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn" style={{ flex: 1, marginTop: 0 }} onClick={copyLink}>
            {copied ? '✅ הועתק!' : '📋 העתק לינק'}
          </button>
          <button
            className="btn btn-success"
            style={{ flex: 1, marginTop: 0 }}
            onClick={shareLink}
          >
            📤 שתף בטלגרם
          </button>
        </div>
      </div>

      {/* How it works */}
      <div className="card" style={{ marginTop: 8 }}>
        <div className="card-title" style={{ marginBottom: 10 }}>איך זה עובד?</div>
        {[
          ['1️⃣', 'שתף את הלינק שלך עם חברים'],
          ['2️⃣', 'החבר לוחץ על הלינק ומצטרף לבוט'],
          ['3️⃣', `אתה מקבל אוטומטית ${data?.bonus ?? 10} חיפושים במתנה`],
        ].map(([num, text]) => (
          <div key={num} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 8 }}>
            <span style={{ fontSize: 18, flexShrink: 0 }}>{num}</span>
            <span style={{ fontSize: 14 }}>{text}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
