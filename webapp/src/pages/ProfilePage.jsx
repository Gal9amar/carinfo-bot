import { useState, useEffect, useRef } from 'react'
import { fetchUserOrders, fetchGarage, fetchReferral, fetchSearchHistory, fetchUserWatches, fetchPackages, deleteMyAccount } from '../api.js'
import { fmtDateLong } from '../utils/time.js'
import { getPlan, formatPlanExpiry, daysLeftLabel, planIcon, globalBenefit as getGlobalBenefit } from '../utils/plan.js'
import BackButton from '../components/BackButton.jsx'

export default function ProfilePage({ user, onNavigate, onBack, onAccountDeleted }) {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState(false)
  const delDialogRef = useRef(null)
  const delTriggerRef = useRef(null)
  const delWasOpen = useRef(false)
  // Move focus into the confirmation when it opens; give it back to the trigger when it closes.
  useEffect(() => {
    if (confirmDelete) { delWasOpen.current = true; delDialogRef.current?.focus() }
    else if (delWasOpen.current) { delWasOpen.current = false; delTriggerRef.current?.focus() }
  }, [confirmDelete])

  const [orders, setOrders]     = useState(null)
  const [garage, setGarage]     = useState(null)
  const [referral, setReferral] = useState(null)
  const [historyCount, setHistoryCount] = useState(null)
  const [watchesCount, setWatchesCount] = useState(null)
  const [packagesCount, setPackagesCount] = useState(null)

  useEffect(() => {
    fetchUserOrders().catch(() => null).then(setOrders)
    fetchGarage().catch(() => null).then(setGarage)
    fetchReferral().catch(() => null).then(setReferral)
    fetchSearchHistory().then(res => setHistoryCount(res?.length)).catch(() => null)
    fetchUserWatches().then(res => setWatchesCount(res?.length)).catch(() => null)
    fetchPackages().then(res => setPackagesCount(res?.length)).catch(() => null)
  }, [])

  if (!user) return <div className="loading"></div>

  const searchesLeft = user.searches_left
  const isUnlimited  = searchesLeft === -1
  const plan         = getPlan(user)
  const isSubscriber = !plan.isFree
  const globalBenefit = getGlobalBenefit(user)
  const fullName     = [user.first_name, user.last_name].filter(Boolean).join(' ') || 'משתמש'

  const ownedCount  = garage?.filter(g => g.status === 'owned').length ?? null
  const ordersCount = orders?.length ?? null

  const tiles = [
    { id: 'orders',   icon: '📦', label: 'היסטוריית הזמנות',   value: ordersCount },
    { id: 'history',  icon: '📋', label: 'היסטוריית חיפושים', value: historyCount },
    { id: 'garage',   icon: '🚘', label: 'רכבים שקניתי',       value: ownedCount },
    { id: 'watches',  icon: '🔔', label: 'ההתראות שלי',       value: watchesCount },
    { id: 'referral', icon: '🤝', label: 'הפנה חבר',           value: referral?.count },
    { id: 'packages', icon: '🛒', label: 'רכישת מוצר',         value: packagesCount },
    { id: 'ticket',   icon: '🎫', label: 'תמיכה' },
    ...(user.is_admin ? [{ id: 'admin', icon: '🛠', label: 'פאנל ניהול' }] : []),
  ]

  const mainTiles = tiles.filter(t => !['ticket', 'admin'].includes(t.id))
  const adminTile = tiles.find(t => t.id === 'admin')
  const quotaPct = isUnlimited ? 100
    : user.searches_quota > 0 ? Math.max(4, Math.min(100, Math.round((searchesLeft / user.searches_quota) * 100)))
    : 0

  return (
    <div className="page" style={{ paddingBottom: 24 }}>
      <BackButton onClick={onBack} />

      {/* Identity */}
      <header style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <h1 style={{
            fontSize: 22, fontWeight: 900, letterSpacing: '-0.5px',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>{fullName}</h1>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2, lineHeight: 1.5 }}>
            {user.username && <div dir="ltr" style={{ textAlign: 'right' }}>@{user.username}</div>}
            {user.first_seen && <div>הצטרף/ה ב-{fmtDateLong(user.first_seen)}</div>}
          </div>
          <span style={{
            display: 'inline-block', maxWidth: '100%', marginTop: 6, borderRadius: 14, padding: '3px 10px', fontSize: 12, fontWeight: 700, lineHeight: 1.4,
            border: '1px solid var(--border)',
            background: isSubscriber ? 'rgba(0, 122, 255, 0.1)' : 'rgba(255,255,255,0.85)',
            color: isSubscriber ? '#0058b0' : 'var(--text-muted)', overflowWrap: 'anywhere',
          }}><span aria-hidden="true">{planIcon(plan)} </span>{plan.name}</span>
        </div>
      </header>

      {/* Plan and quota */}
      <div className="card" style={{ padding: 18, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>יתרת חיפושים</span>
          <span style={{
            fontSize: 26, fontWeight: 900, letterSpacing: '-0.5px',
            color: searchesLeft === 0 ? 'var(--danger)' : 'var(--text-main)',
          }}>{isUnlimited ? '∞' : searchesLeft}</span>
        </div>
        <div aria-hidden="true" style={{ height: 8, borderRadius: 99, background: 'rgba(0, 100, 200, 0.1)', overflow: 'hidden' }}>
          <div style={{
            width: `${quotaPct}%`, height: '100%', borderRadius: 99,
            background: searchesLeft === 0 ? 'var(--danger)' : 'linear-gradient(90deg, #0066d6, #00c6ff)',
          }} />
        </div>
        {plan.expires && (
          <div style={{
            display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap', fontSize: 13, lineHeight: 1.5,
            color: plan.expiringSoon ? '#b45309' : 'var(--text-main)', fontWeight: plan.expiringSoon ? 700 : 500,
          }}>
            <span>{plan.expiringSoon ? '⚠️ ' : ''}בתוקף עד <span dir="ltr" style={{ unicodeBidi: 'isolate' }}>{formatPlanExpiry(plan.expires)}</span></span>
            <span>{daysLeftLabel(plan.daysLeft)}</span>
          </div>
        )}
        {plan.isFixed ? (
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            {plan.kind === 'admin' ? 'גישה מלאה לכל התכונות' : 'ללא תאריך סיום'}
          </div>
        ) : (
          <button
            className={isSubscriber && !plan.expiringSoon ? 'btn btn-outline' : 'btn'}
            style={{ marginTop: 2, padding: 12, minHeight: 44 }}
            onClick={() => onNavigate('packages')}
          >
            {plan.isFree ? 'שדרגו ל-Premium' : plan.kind === 'premium' ? 'ניהול והארכת מסלול' : 'המסלולים שלי'}
          </button>
        )}
      </div>

      {globalBenefit && (
        <div role="note" style={{
          display: 'flex', gap: 10, alignItems: 'flex-start', margin: '0 0 16px', padding: '10px 14px',
          borderRadius: 14, border: '1px dashed var(--border)', background: 'rgba(255,255,255,0.6)',
          fontSize: 12, lineHeight: 1.6, color: 'var(--text-muted)',
        }}>
          <span aria-hidden="true">🎁</span>
          <span style={{ minWidth: 0, overflowWrap: 'anywhere' }}>
            <strong style={{ color: 'var(--text-main)' }}>הטבה כללית לכולם: </strong>{globalBenefit.label}
            {globalBenefit.exp && <> (עד <span dir="ltr" style={{ unicodeBidi: 'isolate' }}>{globalBenefit.exp}</span>)</>}
          </span>
        </div>
      )}

      {/* Navigation tiles */}
      <h2 className="section-label" style={{ marginTop: 8 }}>האזור שלי</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {mainTiles.map(t => (
          <button
            key={t.id}
            onClick={() => onNavigate(t.id)}
            className="card"
            style={{
              margin: 0, padding: '16px 14px', textAlign: 'right', cursor: 'pointer',
              display: 'flex', flexDirection: 'column', gap: 6, borderRadius: 18,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 26, lineHeight: 1 }} aria-hidden="true">{t.icon}</span>
              {t.value != null && (
                <span style={{
                  fontSize: 12, fontWeight: 700, color: 'var(--primary)',
                  background: 'rgba(0, 122, 255, 0.1)', borderRadius: 99, padding: '2px 9px',
                }}>{t.value}</span>
              )}
            </div>
            <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-main)' }}>{t.label}</span>
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginTop: 22 }}>
        {[{ id: 'ticket', label: 'תמיכה' }, { id: 'privacy', label: 'פרטיות' }, { id: 'accessibility', label: 'נגישות' }, { id: 'howItWorks', label: 'איך זה עובד' }].map(l => (
          <button
            key={l.id}
            onClick={() => onNavigate(l.id)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer', fontSize: 13,
              color: 'var(--text-muted)', textDecoration: 'underline', padding: '12px 8px', minHeight: 44,
            }}
          >{l.label}</button>
        ))}
      </div>

      {!user.is_admin && (
        <div style={{ marginTop: 22, textAlign: 'center' }}>
          {!confirmDelete ? (
            <button
              ref={delTriggerRef}
              onClick={() => setConfirmDelete(true)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, color: '#c53030', textDecoration: 'underline', padding: '12px 8px', minHeight: 44 }}
            >מחיקת החשבון וכל הנתונים</button>
          ) : (
            <div className="card" role="alertdialog" aria-labelledby="del-title" tabIndex={-1} ref={delDialogRef} onKeyDown={e => { if (e.key === 'Escape' && !deleting) setConfirmDelete(false) }} style={{ textAlign: 'right', border: '1.5px solid rgba(220,38,38,0.4)' }}>
              <div id="del-title" style={{ fontWeight: 800, fontSize: 15, marginBottom: 6 }}>⚠️ למחוק את החשבון לצמיתות?</div>
              <div style={{ fontSize: 13, lineHeight: 1.7, color: 'var(--text-main)' }}>
                כל הנתונים שנאספו עליך יימחקו: היסטוריית חיפושים, רכבים במוסך, הערות, התראות, תזכורות, פניות תמיכה והזמנות.
                <br />יתרת החיפושים והמנוי יאבדו ולא ניתן יהיה לשחזר אותם.
                <br />רישומי תשלום יישמרו ללא פרטים מזהים, כנדרש בדין.
                <br />כדי להשתמש בבוט שוב תצטרך להפעיל אותו מחדש ולאשר את תנאי השימוש.
              </div>
              {deleteError && <div role="alert" style={{ color: '#c53030', fontSize: 13, marginTop: 8 }}>המחיקה נכשלה. נסה שוב מאוחר יותר.</div>}
              <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                <button className="btn btn-danger" style={{ flex: 1, marginTop: 0 }} disabled={deleting}
                  onClick={async () => {
                    setDeleting(true); setDeleteError(false)
                    try { await deleteMyAccount(); onAccountDeleted && onAccountDeleted() }
                    catch { setDeleteError(true); setDeleting(false) }
                  }}>{deleting ? 'מוחק…' : 'כן, מחק הכול'}</button>
                <button className="btn btn-outline" style={{ flex: 1, marginTop: 0 }} disabled={deleting}
                  onClick={() => setConfirmDelete(false)}>ביטול</button>
              </div>
            </div>
          )}
        </div>
      )}

      {adminTile && (
        <button
          onClick={() => onNavigate('admin')}
          style={{
            width: '100%', marginTop: 18, padding: '12px 14px', borderRadius: 14, cursor: 'pointer',
            border: '1px solid var(--border)', background: 'rgba(255,255,255,0.85)',
            color: 'var(--primary)', fontWeight: 700, fontSize: 14,
          }}
        >🛠 פאנל ניהול</button>
      )}
    </div>
  )
}
