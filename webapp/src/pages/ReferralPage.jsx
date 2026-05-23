import { useState, useEffect } from 'react'
import { fetchReferral, fetchReferrals } from '../api.js'
import BackButton from '../components/BackButton.jsx'

export default function ReferralPage({ onBack }) {
  const [info, setInfo]         = useState(null)
  const [referrals, setReferrals] = useState(null)
  const [tab, setTab]           = useState('share') // 'share' | 'history'
  const [copied, setCopied]     = useState(false)

  useEffect(() => {
    fetchReferral().then(setInfo).catch(() => {})
    fetchReferrals().then(setReferrals).catch(() => {})
  }, [])

  function copyLink() {
    if (!info?.link) return
    navigator.clipboard?.writeText(info.link).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  function shareLink() {
    if (!info?.link) return
    const text = encodeURIComponent('הצטרף לבוט בדיקת הרכבים הכי טוב בישראל! 🚗')
    const url  = encodeURIComponent(info.link)
    window.Telegram?.WebApp?.openTelegramLink?.(`https://t.me/share/url?url=${url}&text=${text}`)
  }

  function fmtDate(ts) {
    if (!ts) return ''
    try {
      const d = new Date(ts.replace(' ', 'T') + (ts.includes('+') ? '' : 'Z'))
      return d.toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit', year: '2-digit' })
    } catch { return ts.slice(0, 10) }
  }

  const totalBonus = (referrals || []).reduce((s, r) => s + r.bonus, 0)

  return (
    <div className="page">
      {onBack && <BackButton onClick={onBack} />}
      <div className="page-title">🤝 הפנה חבר</div>

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 16 }}>
        <div className="stat-card">
          <div className="stat-value">{info?.count ?? '—'}</div>
          <div className="stat-label">הצטרפו</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{totalBonus || '—'}</div>
          <div className="stat-label">חיפושים הרווחת</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{info?.bonus ?? '—'}</div>
          <div className="stat-label">בונוס להפניה</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
        {[['share', '🔗 שיתוף'], ['history', '📋 הפניות שלי']].map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              flex: 1, padding: '8px 4px', border: 'none', borderRadius: 10, cursor: 'pointer',
              background: tab === id ? 'var(--btn)' : 'var(--bg2)',
              color: tab === id ? 'var(--btn-text)' : 'var(--hint)',
              fontSize: 13, fontWeight: tab === id ? 600 : 400,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Share tab */}
      {tab === 'share' && (
        <div>
          <div style={{
            background: 'linear-gradient(135deg,#2481cc,#1a5fa8)',
            borderRadius: 14, padding: '16px', marginBottom: 14, color: '#fff', textAlign: 'center',
          }}>
            <div style={{ fontSize: 32, marginBottom: 6 }}>🎁</div>
            <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>
              הפנה חברים — קבל {info?.bonus ?? 10} חיפושים לכל הצטרפות
            </div>
            <div style={{ fontSize: 13, opacity: 0.85 }}>
              כל חבר שמצטרף לבוט דרך הלינק שלך<br />מוסיף לך {info?.bonus ?? 10} חיפושים אוטומטית
            </div>
          </div>

          <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 8 }}>הלינק האישי שלך:</div>
          <div style={{
            background: 'var(--bg2)', borderRadius: 10, padding: '10px 12px',
            fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-all',
            color: 'var(--text)', marginBottom: 10, direction: 'ltr', textAlign: 'left',
          }}>
            {info?.link ?? '⏳ טוען...'}
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <button className="btn" style={{ flex: 1, marginTop: 0 }} onClick={copyLink}>
              {copied ? '✅ הועתק!' : '📋 העתק'}
            </button>
            <button className="btn btn-success" style={{ flex: 1, marginTop: 0 }} onClick={shareLink}>
              📤 שתף בטלגרם
            </button>
          </div>

          <div className="card">
            <div className="card-title" style={{ marginBottom: 10 }}>איך זה עובד?</div>
            {[
              ['1️⃣', 'שלח את הלינק לחבר'],
              ['2️⃣', 'החבר לוחץ ומצטרף לבוט'],
              ['3️⃣', `אתה מקבל ${info?.bonus ?? 10} חיפושים במתנה אוטומטית`],
            ].map(([num, text]) => (
              <div key={num} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 8 }}>
                <span style={{ fontSize: 18, flexShrink: 0 }}>{num}</span>
                <span style={{ fontSize: 14 }}>{text}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* History tab */}
      {tab === 'history' && (
        <div>
          {referrals === null && <div className="loading">⏳ טוען...</div>}

          {referrals !== null && referrals.length === 0 && (
            <div style={{ textAlign: 'center', padding: '32px 16px' }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🤝</div>
              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>עדיין אין הפניות</div>
              <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 20 }}>
                שלח את הלינק לחברים וכאן תראה מי הצטרף
              </div>
              <button className="btn" onClick={() => setTab('share')}>🔗 לשיתוף</button>
            </div>
          )}

          {referrals !== null && referrals.length > 0 && (
            <>
              <div style={{ fontSize: 13, color: 'var(--hint)', marginBottom: 10 }}>
                {referrals.length} חברים הצטרפו · סה"כ {totalBonus} חיפושים הרווחת
              </div>
              {referrals.map(ref => (
                <div key={ref.id} style={{
                  background: 'var(--card-bg, rgba(255,255,255,0.05))',
                  borderRadius: 12, padding: '12px 14px', marginBottom: 8,
                  display: 'flex', alignItems: 'center', gap: 12,
                  borderRight: '3px solid #38a169',
                }}>
                  <div style={{
                    width: 38, height: 38, borderRadius: '50%',
                    background: 'linear-gradient(135deg,#2481cc,#1a5fa8)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 18, flexShrink: 0,
                  }}>
                    👤
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 2 }}>
                      {ref.name}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--hint)' }}>
                      הצטרף · {fmtDate(ref.joined_at)}
                    </div>
                  </div>
                  <div style={{ textAlign: 'left', flexShrink: 0 }}>
                    <div style={{
                      background: '#38a16920', color: '#38a169',
                      borderRadius: 20, padding: '3px 10px',
                      fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap',
                    }}>
                      ✅ +{ref.bonus} חיפושים
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  )
}
