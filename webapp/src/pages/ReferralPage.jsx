import { useState, useEffect } from 'react'
import { fetchReferral, fetchReferrals } from '../api.js'
import { fmtDate as fmtDateIL } from '../utils/time.js'
import BackButton from '../components/BackButton.jsx'
import PageBanners from '../components/PageBanners.jsx'

export default function ReferralPage({ onBack, onNavigate }) {
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

  function fmtDate(ts) { return fmtDateIL(ts) }

  const totalBonus = (referrals || []).reduce((s, r) => s + r.bonus, 0)

  return (
    <div className="page">
      {onBack && <BackButton onClick={onBack} />}
      <div className="page-title">🤝 הפנה חבר</div>

      <PageBanners page="referral" onNavigate={onNavigate} />

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
      <div className="card" style={{ display: 'flex', gap: 6, marginBottom: 24, padding: '6px' }}>
        {[['share', '🔗 שיתוף'], ['history', '📋 הפניות שלי']].map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            style={{
              flex: 1, padding: '10px 4px', border: 'none', borderRadius: 12, cursor: 'pointer',
              background: tab === id ? 'var(--primary)' : 'transparent',
              color: tab === id ? '#fff' : 'var(--hint)',
              fontSize: 14, fontWeight: tab === id ? 700 : 500,
              boxShadow: tab === id ? '0 4px 12px rgba(0, 122, 255, 0.3)' : 'none',
              transition: '0.2s',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Share tab */}
      {tab === 'share' && (
        <>
          <div className="card" style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 13, color: 'var(--text)', marginBottom: 8, fontWeight: 600 }}>הלינק האישי שלך:</div>
            <div style={{
              background: 'rgba(255, 255, 255, 0.5)', border: '1px solid rgba(0,0,0,0.05)',
              borderRadius: 12, padding: '14px 16px',
              fontFamily: 'monospace', fontSize: 13, wordBreak: 'break-all',
              color: 'var(--primary)', marginBottom: 16, direction: 'ltr', textAlign: 'left',
            }}>
              {info?.link ?? '⏳ טוען...'}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-secondary" style={{ flex: 1, marginTop: 0 }} onClick={copyLink}>
                {copied ? '✅ הועתק!' : '📋 העתק'}
              </button>
              <button className="btn" style={{ flex: 1, marginTop: 0, background: '#34c759', boxShadow: '0 6px 20px rgba(52, 199, 89, 0.35)' }} onClick={shareLink}>
                📤 שתף בטלגרם
              </button>
            </div>
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
        </>
      )}

      {/* History tab */}
      {tab === 'history' && (
        <div>
          {referrals === null && <div className="loading"></div>}

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
