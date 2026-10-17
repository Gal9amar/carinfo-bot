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
  const totalDays  = (referrals || []).reduce((s, r) => s + (r.bonus_days || 0), 0)
  const premium    = !!info?.premium

  return (
    <div className="page">
      {onBack && <BackButton onClick={onBack} />}
      <h1 className="page-title">🤝 הפנה חבר</h1>

      <PageBanners page="referral" onNavigate={onNavigate} />

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 16 }}>
        <div className="stat-card">
          <div className="stat-value">{info?.count ?? '—'}</div>
          <div className="stat-label">הצטרפו</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{premium ? (totalDays || '—') : (totalBonus || '—')}</div>
          <div className="stat-label">{premium ? 'ימי Premium הרווחת' : 'חיפושים הרווחת'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{premium ? (info?.bonus_days ?? '—') : (info?.bonus ?? '—')}</div>
          <div className="stat-label">בונוס להפניה</div>
        </div>
      </div>

      {/* Tabs */}
      <div role="tablist" aria-label="תצוגות הפניות" style={{ display: 'flex', gap: 2, marginBottom: 20, padding: 3, borderRadius: 14, background: 'rgba(0, 100, 200, 0.08)' }}>
        {[['share', '🔗 שיתוף'], ['history', '📋 הפניות שלי']].map(([id, label]) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            style={{
              flex: 1, padding: '9px 4px', border: 'none', borderRadius: 11, cursor: 'pointer',
              background: tab === id ? '#fff' : 'transparent',
              color: tab === id ? 'var(--text-main)' : 'var(--text-muted)',
              fontSize: 14, fontWeight: tab === id ? 700 : 500,
              boxShadow: tab === id ? '0 1px 4px rgba(0,0,0,0.12)' : 'none',
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
              background: 'rgba(255, 255, 255, 0.5)', border: '1px solid var(--border)',
              borderRadius: 12, padding: '14px 16px',
              fontFamily: 'monospace', fontSize: 13, wordBreak: 'break-all',
              color: 'var(--primary)', marginBottom: 16, direction: 'ltr', textAlign: 'left',
            }}>
              {info?.link ?? '⏳ טוען...'}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-secondary" style={{ flex: 1, marginTop: 0 }} onClick={copyLink}>
                {copied ? <span role="status">✅ הועתק!</span> : '📋 העתק'}
              </button>
              <button className="btn" style={{ flex: 1, marginTop: 0, background: '#177a33', boxShadow: '0 6px 20px rgba(23, 122, 51, 0.35)' }} onClick={shareLink}>
                📤 שתף בטלגרם
              </button>
            </div>
          </div>

          <div className="card">
            <div className="card-title" style={{ marginBottom: 10 }}>איך זה עובד?</div>
            {[
              'שלח את הלינק לחבר',
              'החבר לוחץ ומצטרף לבוט',
              premium ? `המסלול שלך מוארך אוטומטית ב-${info?.bonus_days} ימים` : `אתה מקבל ${info?.bonus ?? 10} חיפושים במתנה אוטומטית`,
            ].map((text, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 10 }}>
                <span style={{
                  width: 26, height: 26, borderRadius: '50%', flexShrink: 0, color: '#fff',
                  background: 'var(--grad-primary)', fontSize: 12, fontWeight: 700,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>{i + 1}</span>
                <span style={{ fontSize: 14 }}>{text}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* History tab */}
      {tab === 'history' && (
        <div>
          {referrals === null && <div className="loading" role="status" aria-label="טוען"></div>}

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
                <div key={ref.id} className="card" style={{
                  padding: '12px 14px', marginBottom: 10,
                  display: 'flex', alignItems: 'center', gap: 12,
                }}>
                  <div style={{
                    width: 38, height: 38, borderRadius: '50%',
                    background: 'rgba(0, 122, 255, 0.1)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 18, flexShrink: 0,
                  }} aria-hidden="true">
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
                      background: '#177a3320', color: '#177a33',
                      borderRadius: 20, padding: '3px 10px',
                      fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap',
                    }}>
                      {ref.bonus_days > 0 ? `✅ +${ref.bonus_days} ימים` : `✅ +${ref.bonus} חיפושים`}
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
