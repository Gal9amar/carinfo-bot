import { useState, useEffect } from 'react'
import { getPlan, formatPlanExpiry, daysLeftLabel, planIcon } from '../utils/plan.js'
import BackButton from '../components/BackButton.jsx'
import PageBanners from '../components/PageBanners.jsx'
import { fetchProducts } from '../api.js'
import { safeDescriptionHtml } from '../utils/safeHtml.js'

// Same lines, same order on the FREE and Premium cards; premiumOnly lines are ✗ on FREE.
const PLAN_FEATURES = [
  ['נתוני רכב מלאים — שנה, דגם, בעלות, טסט, ק״מ', false],
  ['היסטוריית חיפושים אישית', false],
  ['השוואת רכבים', false],
  ['תזכורת טסט וניהול ״רכבים שקניתי״', false],
  ['חיפושים ללא הגבלה', true],
  ['מחיר שוק Yad2', true],
  ['התראות על מודעות חדשות ב-Yad2', true],
  ['דוח PDF מפורט', true],
  ['גישה לכל פיצ׳רי הפרימיום העתידיים', true],
]
const FREE_FEATURES = PLAN_FEATURES.map(([text, premiumOnly]) => ({ text, included: !premiumOnly }))
const PREMIUM_FEATURES = PLAN_FEATURES.map(([text]) => ({ text, included: true }))

export default function PackagesPage({ packages, user, highlightProductId, onSelect, onPrivacy, onSupport, onReferral, onBack, onNavigate }) {
  const [quantities, setQuantities] = useState({})
  const [products, setProducts] = useState([])
  function getQty(id) { return quantities[id] ?? 1 }
  function setQty(id, val, max = 10) {
    setQuantities(q => ({ ...q, [id]: Math.max(1, Math.min(max, val)) }))
  }

  useEffect(() => { fetchProducts().then(setProducts).catch(() => setProducts([])) }, [])

  useEffect(() => {
    if (!highlightProductId || products.length === 0) return
    const el = document.getElementById(`product-${highlightProductId}`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [highlightProductId, products])

  function handleSelect(pkg) { onSelect(pkg) }
  function handleSelectProduct(p, qty = 1) { onSelect({ ...p, label: p.name, _isProduct: true, _qty: qty }) }

  const plan       = getPlan(user)
  const isFreeUser = !!plan?.isFree
  const subLabel   = plan?.kind === 'searches' ? plan.name : null

  const freePackage    = packages.find(p => p.searches === 0 && (p.package_type ?? 'searches') === 'searches')
  const alertPackages  = packages.filter(p => p.package_type === 'alerts')
  const paidPackages   = packages.filter(p => p.searches !== 0 && (p.package_type ?? 'searches') === 'searches')

  return (
    <div className="page" style={{ paddingBottom: 16 }}>
      {onBack && <BackButton onClick={onBack} />}
      <h1 className="page-title">🛒 החנות</h1>

      <PageBanners page="packages" onNavigate={onNavigate} />

      {user && plan && (
        <div className="card" style={{ marginBottom: 16 }} aria-label="המסלול שלך">
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            {user.first_name ? `שלום ${user.first_name} · ` : ''}המסלול שלך
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginTop: 4 }}>
            <span style={{ fontWeight: 800, fontSize: 17, minWidth: 0, overflowWrap: 'anywhere' }}>
              <span aria-hidden="true">{planIcon(plan)} </span>{plan.name}
            </span>
            <span style={{ flexShrink: 0, fontSize: 13, color: 'var(--text-muted)' }}>
              <strong style={{ color: 'var(--primary)', fontSize: 18 }}>{user.searches_left === -1 ? '∞' : (user.searches_left ?? 0)}</strong> חיפושים
            </span>
          </div>
          {plan.expires && (
            <div style={{
              marginTop: 8, fontSize: 13, lineHeight: 1.5,
              color: plan.expiringSoon ? '#b45309' : 'var(--text-main)', fontWeight: plan.expiringSoon ? 700 : 500,
            }}>
              {plan.expiringSoon ? '⚠️ ' : ''}בתוקף עד <span dir="ltr" style={{ unicodeBidi: 'isolate' }}>{formatPlanExpiry(plan.expires)}</span> · {daysLeftLabel(plan.daysLeft)}
            </div>
          )}
        </div>
      )}

      {/* What is the Premium plan */}
      <div style={{
        background: 'linear-gradient(135deg,#7928ca18,#5a1e9908)',
        border: '1px solid #7928ca33',
        borderRadius: 16, padding: '16px 18px', marginBottom: 20,
      }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10, color: '#0066d6' }}>
          ⭐ מה זה מסלול Premium?
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 9, fontSize: 13 }}>
          <Row icon="♾️" text="חיפושים ללא הגבלה למשך חודש מיום הפעלת המסלול" />
          <Row icon="🔓" text="כל פיצ'רי הפרימיום פתוחים: מחיר שוק, התראות על מודעות חדשות ב-Yad2 ודוח PDF — וכל פיצ'ר פרימיום שיתווסף בעתיד ייפתח לך אוטומטית" />
          <Row icon="⚖️" text="השוואת רכבים פתוחה לכל המשתמשים, גם בלי מסלול" />
          <Row icon="💳" text="תשלום חד-פעמי — אין חיוב חוזר ואין חידוש אוטומטי" />
          <Row icon="⏳" text="המסלול פעיל עד תאריך הסיום המוצג באזור האישי, ולאחריו חוזרים למסלול החינמי" />
          <Row icon="🤝" text="מזמינים חברים? מנוי Premium מקבל ימים נוספים במסלול על כל חבר שמצטרף" />
        </div>

        <div style={{
          marginTop: 14, padding: '10px 14px',
          background: 'rgba(56,161,105,0.12)', borderRadius: 10,
          fontSize: 12, color: '#177a33', fontWeight: 600,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span style={{ fontSize: 16 }}>✅</span>
          <span>המסלול מופעל בחשבונך לאחר אישור התשלום</span>
        </div>
      </div>

      {/* ── Section: מוצרים דיגיטליים ── */}
      {products.length > 0 && (
        <>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14, color: 'var(--text)' }}>
            🛍️ מוצרים דיגיטליים
          </div>
          {products.map(p => {
            const accent = '#0066d6'
            const grad   = 'linear-gradient(135deg,#1e40af,#0b6fc2)'
            const maxQty = Math.max(1, Math.min(10, p.stock_count ?? 1))
            const qty    = Math.min(getQty(p.id), maxQty)
            const totalPrice = p.price * qty
            const isComingSoon = p.availability_status === 'coming_soon'
            const isBuyable = p.in_stock && !isComingSoon
            const ribbon = isComingSoon ? { text: '🔜 בקרוב', bg: '#2b6cb0' } : !p.in_stock ? { text: 'אזל המלאי', bg: '#c53030' } : null
            const isHighlighted = String(highlightProductId) === String(p.id)
            return (
              <div key={p.id} id={`product-${p.id}`} style={{
                borderRadius: 20, overflow: 'hidden', marginBottom: 22, position: 'relative',
                boxShadow: isHighlighted
                  ? '0 4px 18px rgba(20,60,120,0.08), 0 0 0 2px #0066d6'
                  : '0 4px 18px rgba(20,60,120,0.08), 0 0 0 1px rgba(0,100,200,0.18)',
                background: 'var(--bg2)',
              }}>
                {ribbon && (
                  <div style={{
                    position: 'absolute', top: 10, left: 10, zIndex: 1,
                    background: ribbon.bg, color: '#fff', fontSize: 11, fontWeight: 700,
                    borderRadius: 20, padding: '3px 10px',
                  }}>{ribbon.text}</div>
                )}
                <div style={{ position: 'relative', height: p.image_url ? 170 : 150, opacity: isBuyable ? 1 : 0.6 }}>
                  {p.image_url
                    ? <img loading="lazy" decoding="async" src={p.image_url} alt={p.name}
                        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                    : <div style={{ width: '100%', height: '100%', background: grad,
                        display: 'flex', flexDirection: 'column',
                        alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                        <span style={{ fontSize: 52, lineHeight: 1 }}>📦</span>
                      </div>
                  }
                  <div style={{
                    position: 'absolute', inset: 0,
                    background: 'linear-gradient(to top, rgba(0,0,0,0.72) 0%, transparent 55%)',
                    display: 'flex', alignItems: 'flex-end', padding: '12px 14px',
                  }}>
                    <span style={{
                      fontSize: 13, fontWeight: 400, padding: '4px 12px',
                      background: accent, color: '#fff', borderRadius: 20, whiteSpace: 'nowrap',
                    }}>📦 {p.name}</span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 7, padding: '14px 14px 10px', flexWrap: 'wrap' }}>
                  <Chip accent={accent}>{p.delivery_type === 'auto' ? '⚡ אספקה מיידית' : '🕐 אספקה ידנית'}</Chip>
                  {p.delivery_time_note && <Chip accent={accent}>⏱ {p.delivery_time_note}</Chip>}
                  {p.in_stock && <Chip accent={accent}>📦 במלאי: {p.stock_count}</Chip>}
                </div>

                {p.description && (
                  <>
                    <div style={{ height: 1, background: 'rgba(0,100,200,0.12)', margin: '0 14px' }} />
                    <div
                      style={{ padding: '12px 16px', fontSize: 13, color: 'var(--hint)', lineHeight: 1.7 }}
                      dangerouslySetInnerHTML={{ __html: safeDescriptionHtml(p.description) }}
                    />
                  </>
                )}

                {p.features?.length > 0 && (
                  <>
                    <div style={{ height: 1, background: 'rgba(0,100,200,0.12)', margin: '0 14px' }} />
                    <div style={{ padding: '12px 16px', fontSize: 13, lineHeight: 1.9 }}>
                      {p.features.map((f, i) => {
                        if (f.state === 'plain') {
                          return <div key={i} style={{ color: 'var(--hint)' }}>{f.text}</div>
                        }
                        const included = f.state === 'included'
                        return (
                          <div key={i} style={{ color: included ? 'var(--hint)' : '#c53030' }}>
                            {included ? '✅' : '✗'} {f.text}
                          </div>
                        )
                      })}
                    </div>
                  </>
                )}

                {isBuyable && maxQty > 1 && (
                  <>
                    <div style={{ height: 1, background: 'rgba(0,100,200,0.12)', margin: '0 14px' }} />
                    <div style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '12px 16px',
                    }}>
                      <span style={{ fontSize: 13, color: 'var(--hint)' }}>כמות</span>
                      <div style={{ display: 'flex', alignItems: 'center',
                        background: 'var(--bg)', borderRadius: 12, overflow: 'hidden' }}>
                        <button onClick={() => setQty(p.id, qty - 1, maxQty)} aria-label="הפחת כמות" disabled={qty <= 1} style={{
                          width: 44, height: 40, border: 'none', background: 'transparent',
                          fontSize: 22, cursor: qty <= 1 ? 'default' : 'pointer',
                          color: qty <= 1 ? 'var(--hint)' : accent, fontWeight: 700,
                        }}>−</button>
                        <span style={{ width: 34, textAlign: 'center', fontWeight: 800, fontSize: 16 }} role="status" aria-label={`כמות ${qty}`}>{qty}</span>
                        <button onClick={() => setQty(p.id, qty + 1, maxQty)} aria-label="הוסף כמות" disabled={qty >= maxQty} style={{
                          width: 44, height: 40, border: 'none', background: 'transparent',
                          fontSize: 22, cursor: qty >= maxQty ? 'default' : 'pointer',
                          color: qty >= maxQty ? 'var(--hint)' : accent, fontWeight: 700,
                        }}>+</button>
                      </div>
                      <span style={{ fontSize: 13, color: 'var(--hint)' }}>
                        מקסימום <strong style={{ color: 'var(--text)' }}>{maxQty}</strong>
                      </span>
                    </div>
                  </>
                )}

                <div style={{ padding: '10px 14px 16px' }}>
                  <div style={{
                    display: 'flex', alignItems: 'baseline', justifyContent: 'center',
                    gap: 6, marginBottom: 12,
                  }}>
                    <span style={{ fontSize: 40, fontWeight: 900, color: accent, lineHeight: 1 }}>
                      ₪{totalPrice}
                    </span>
                    {qty > 1 && (
                      <span style={{ fontSize: 12, color: 'var(--hint)' }}>({qty} × ₪{p.price})</span>
                    )}
                  </div>
                  <button
                    onClick={() => handleSelectProduct(p, qty)}
                    disabled={!isBuyable}
                    style={{
                      width: '100%', padding: '14px 0', border: 'none', borderRadius: 14,
                      background: isBuyable ? grad : 'var(--bg)',
                      color: isBuyable ? '#fff' : 'var(--hint)', fontSize: 16, fontWeight: 700,
                      cursor: isBuyable ? 'pointer' : 'default',
                      boxShadow: isBuyable ? '0 4px 14px rgba(20,60,120,0.2)' : 'none',
                      letterSpacing: 0.4,
                    }}
                  >{isComingSoon ? '🔜 בקרוב' : isBuyable ? '🛍️ רכישה' : 'אזל המלאי'}</button>
                </div>
              </div>
            )
          })}
        </>
      )}

      {/* ── FREE card ── */}
      {(() => {
        const freeAccent = '#177a33'
        const freeGrad   = 'linear-gradient(135deg,#1b4332,#2d6a4f)'
        const searchesLeft = user?.searches_left ?? 0
        return (
          <div aria-current={isFreeUser ? 'true' : undefined} style={{
            borderRadius: 20, overflow: 'hidden', marginBottom: 22,
            boxShadow: isFreeUser
              ? '0 4px 18px rgba(20,60,120,0.08), 0 0 0 2px #2e7d32'
              : '0 4px 18px rgba(20,60,120,0.08), 0 0 0 1px rgba(0,100,200,0.18)',
            background: 'var(--bg2)',
          }}>
            {isFreeUser && (
              <div style={{
                background: 'linear-gradient(90deg,#2e7d32,#2e7d32)',
                padding: '6px 14px', fontSize: 12, fontWeight: 700, color: '#fff',
                display: 'flex', alignItems: 'center', gap: 6,
              }}>✓ המסלול הנוכחי שלך</div>
            )}

            {/* Hero */}
            <div style={{
              position: 'relative', height: freePackage?.image_url ? 170 : 150,
            }}>
              {freePackage?.image_url
                ? <img loading="lazy" decoding="async" src={freePackage.image_url} alt="FREE"
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                : <div style={{
                    width: '100%', height: '100%', background: freeGrad,
                    display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: 6,
                  }}>
                    {isFreeUser ? (
                      <>
                        <span style={{ fontSize: 52, fontWeight: 900, color: '#fff', lineHeight: 1 }}>
                          {searchesLeft}
                        </span>
                        <span style={{ color: '#fff', fontSize: 13, fontWeight: 600 }}>
                          חיפושים נותרו
                        </span>
                      </>
                    ) : (
                      <>
                        <span style={{ fontSize: 52, lineHeight: 1 }}>🆓</span>
                        <span style={{ color: '#fff', fontSize: 13, fontWeight: 600 }}>
                          גישה חינמית
                        </span>
                      </>
                    )}
                  </div>
              }
              <div style={{
                position: 'absolute', inset: 0,
                background: 'linear-gradient(to top, rgba(0,0,0,0.65) 0%, transparent 55%)',
                display: 'flex', alignItems: 'flex-end', padding: '12px 14px',
              }}>
                <span style={{
                  fontSize: 13, fontWeight: 400, padding: '4px 12px',
                  background: freeAccent, color: '#fff', borderRadius: 20, whiteSpace: 'nowrap',
                }}>🆓 {freePackage?.label || 'מסלול FREE'}</span>
              </div>
            </div>

            {/* Chips */}
            <div style={{ display: 'flex', gap: 7, padding: '14px 14px 10px', flexWrap: 'wrap' }}>
              {isFreeUser
                ? <Chip accent={freeAccent}>🔍 {searchesLeft} חיפושים נותרו</Chip>
                : <Chip accent={freeAccent}>🔍 חיפושים בהצטרפות</Chip>
              }
              {(freePackage?.chips?.length
                ? freePackage.chips
                : ['🤝 +חיפושים על הפניות', '🔓 ללא תפוגה']
              ).map((c, i) => <Chip key={i} accent={freeAccent}>{c}</Chip>)}
            </div>

            <div style={{ height: 1, background: 'rgba(0,100,200,0.12)', margin: '0 14px' }} />

            {/* Info — dynamic from DB, fallback to hardcoded */}
            <div style={{ padding: '12px 16px', fontSize: 13, lineHeight: 1.9 }}>
              {(freePackage?.features?.length
                ? freePackage.features
                : FREE_FEATURES
              ).map((f, i) => {
                const text = typeof f === 'string' ? f : f.text
                const included = typeof f === 'string' ? true : f.included
                return (
                  <div key={i} style={{ color: included ? 'var(--hint)' : '#c53030' }}>
                    {included ? '✅' : '✗'} {text}
                  </div>
                )
              })}
            </div>

            {/* CTA */}
            <div style={{ padding: '10px 14px 16px' }}>
              {isFreeUser ? (
                <>
                  <div style={{
                    width: '100%', padding: '14px 0', borderRadius: 14, textAlign: 'center',
                    background: 'rgba(0,100,200,0.08)', color: 'var(--text-main)', fontSize: 15, fontWeight: 700,
                  }}>✓ המסלול הפעיל</div>
                  <button
                    onClick={onReferral}
                    style={{
                      width: '100%', minHeight: 44, marginTop: 8, border: 'none', background: 'none',
                      color: 'var(--primary)', fontSize: 14, fontWeight: 700, cursor: 'pointer',
                    }}
                  >🤝 קבלו עוד חיפושים חינם</button>
                </>
              ) : (
                <button
                  onClick={onReferral}
                  style={{
                    width: '100%', padding: '14px 0', border: 'none', borderRadius: 14,
                    background: freeGrad, color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer',
                    boxShadow: '0 4px 14px rgba(20,60,120,0.2)',
                  }}
                >🤝 קבל עוד חיפושים חינם</button>
              )}
            </div>
          </div>
        )
      })()}

      {/* ── Section header: מסלולי מנוי ── */}
      <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14, color: 'var(--text)' }}>
        ⭐ מסלולי מנוי
      </div>

      {paidPackages.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--hint)', fontSize: 14 }}>
          אין חבילות זמינות כרגע
        </div>
      )}

      {paidPackages.map((pkg) => {
        const qty           = getQty(pkg.id)
        const isUnlimited   = pkg.searches === -1
        const totalPrice    = pkg.price * qty
        const totalSearches = isUnlimited ? '∞' : pkg.searches * qty

        const grad   = 'linear-gradient(135deg,#1e40af,#0b6fc2)'
        const accent = '#0066d6'

        const isCurrentPlan = !!plan && (plan.isPremium
          ? isUnlimited && pkg.id === paidPackages.find(p => p.searches === -1)?.id
          : !!subLabel && (subLabel === pkg.label || subLabel.startsWith(pkg.label + ' ×')))
        const isFixedActive = isCurrentPlan && plan.isFixed

        return (
          <div key={pkg.id} aria-current={isCurrentPlan ? 'true' : undefined} style={{
            borderRadius: 20, overflow: 'hidden', marginBottom: 22,
            boxShadow: isCurrentPlan
              ? '0 4px 18px rgba(20,60,120,0.08), 0 0 0 2px #2e7d32'
              : '0 4px 18px rgba(20,60,120,0.08), 0 0 0 1px rgba(0,100,200,0.18)',
            background: 'var(--bg2)',
          }}>

          {isCurrentPlan && (
            <div style={{
              background: 'linear-gradient(90deg,#2e7d32,#2e7d32)',
              padding: '6px 14px', fontSize: 12, fontWeight: 700, color: '#fff',
              display: 'flex', alignItems: 'center', gap: 6,
            }}>{plan.isPremium ? '✓ המסלול הפעיל שלך ✓' : '✓ המסלול הנוכחי שלך'}</div>
          )}
          {isCurrentPlan && plan.expires && (
            <div style={{
              padding: '8px 14px', fontSize: 13, fontWeight: 600, lineHeight: 1.5,
              background: plan.expiringSoon ? 'rgba(255,149,0,0.14)' : 'rgba(46,125,50,0.08)',
              color: plan.expiringSoon ? '#b45309' : '#1b5e20',
            }}>
              {plan.expiringSoon ? '⚠️ ' : ''}בתוקף עד <span dir="ltr" style={{ unicodeBidi: 'isolate' }}>{formatPlanExpiry(plan.expires)}</span> · {daysLeftLabel(plan.daysLeft)}
            </div>
          )}

            {/* ── Hero ── */}
            <div style={{ position: 'relative', height: pkg.image_url ? 170 : 150 }}>
              {pkg.image_url
                ? <img loading="lazy" decoding="async" src={pkg.image_url} alt={pkg.label}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                : <div style={{ width: '100%', height: '100%', background: grad,
                    display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                    <span style={{ fontSize: 52, lineHeight: 1 }}>{isUnlimited ? '♾️' : '⭐'}</span>
                    <span style={{ color: '#fff', fontSize: 13, fontWeight: 600 }}>
                      {isUnlimited ? 'גישה ללא הגבלת כמות' : `${pkg.searches} חיפושים`}
                    </span>
                  </div>
              }
              {/* Dark overlay + tier badge at bottom-left of hero */}
              <div style={{
                position: 'absolute', inset: 0,
                background: 'linear-gradient(to top, rgba(0,0,0,0.72) 0%, transparent 55%)',
                display: 'flex', alignItems: 'flex-end',
                padding: '12px 14px',
              }}>
                <span style={{
                  fontSize: 13, fontWeight: 400, padding: '4px 12px',
                  background: accent, color: '#fff',
                  borderRadius: 20, whiteSpace: 'nowrap',
                }}>⭐ {pkg.label}</span>
              </div>
            </div>

            {/* ── Perks row ── */}
            <div style={{
              display: 'flex', gap: 7, padding: '14px 14px 10px', flexWrap: 'wrap',
            }}>
              {(pkg.chips?.length
                ? pkg.chips
                : [
                    isUnlimited ? '♾️ ללא הגבלה' : `🔍 ${pkg.searches} חיפושים`,
                    '💳 חד-פעמי',
                    isUnlimited ? `📅 תוקף ${(pkg.duration_months ?? 1) > 1 ? `${pkg.duration_months} חודשים` : 'חודש'}` : '🔓 ללא תפוגה',
                  ]
              ).map((c, i) => <Chip key={i} accent={accent}>{c}</Chip>)}
            </div>

            <div style={{ height: 1, background: 'rgba(0,100,200,0.12)', margin: '0 14px' }} />

            {/* ── Features ── */}
            <div style={{ padding: '12px 16px', fontSize: 13, lineHeight: 1.9 }}>
              {(pkg.features?.length
                ? pkg.features
                : PREMIUM_FEATURES
              ).map((f, i) => {
                const text = typeof f === 'string' ? f : f.text
                const included = typeof f === 'string' ? true : f.included
                return (
                  <div key={i} style={{ color: included ? 'var(--hint)' : '#c53030' }}>
                    {included ? '✅' : '✗'} {text}
                  </div>
                )
              })}
            </div>

            <div style={{ height: 1, background: 'rgba(0,100,200,0.12)', margin: '0 14px' }} />
            {!isUnlimited && (
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '12px 16px',
              }}>
                <span style={{ fontSize: 13, color: 'var(--hint)' }}>כמות</span>
                <div style={{ display: 'flex', alignItems: 'center',
                  background: 'var(--bg)', borderRadius: 12, overflow: 'hidden' }}>
                  <button onClick={() => setQty(pkg.id, qty - 1)} aria-label="הפחת כמות" disabled={qty <= 1} style={{
                    width: 44, height: 40, border: 'none', background: 'transparent',
                    fontSize: 22, cursor: qty <= 1 ? 'default' : 'pointer',
                    color: qty <= 1 ? 'var(--hint)' : accent, fontWeight: 700,
                  }}>−</button>
                  <span style={{ width: 34, textAlign: 'center', fontWeight: 800, fontSize: 16 }} role="status" aria-label={`כמות ${qty}`}>{qty}</span>
                  <button onClick={() => setQty(pkg.id, qty + 1)} aria-label="הוסף כמות" disabled={qty >= 10} style={{
                    width: 44, height: 40, border: 'none', background: 'transparent',
                    fontSize: 22, cursor: qty >= 10 ? 'default' : 'pointer',
                    color: qty >= 10 ? 'var(--hint)' : accent, fontWeight: 700,
                  }}>+</button>
                </div>
                <span style={{ fontSize: 13, color: 'var(--hint)' }}>
                  סה״כ <strong style={{ color: 'var(--text)' }}>{totalSearches}</strong>
                </span>
              </div>
            )}

            {/* ── Price + CTA ── */}
            <div style={{ padding: '10px 14px 16px' }}>
              <div style={{
                display: 'flex', alignItems: 'baseline', justifyContent: 'center',
                gap: 6, marginBottom: 12,
              }}>
                <span style={{ fontSize: 40, fontWeight: 900, color: accent, lineHeight: 1 }}>
                  ₪{totalPrice}
                </span>
                {qty > 1 && (
                  <span style={{ fontSize: 12, color: 'var(--hint)' }}>({qty} × ₪{pkg.price})</span>
                )}
              </div>
              {isFixedActive ? (
                <div style={{
                  width: '100%', padding: '14px 0', borderRadius: 14, textAlign: 'center',
                  background: 'rgba(46,125,50,0.1)', color: '#1b5e20', fontSize: 15, fontWeight: 700,
                }}>✓ המסלול פעיל — אין צורך ברכישה</div>
              ) : (
              <button
                onClick={() => handleSelect(pkg)}
                style={{
                  width: '100%', padding: '14px 0', border: 'none', borderRadius: 14,
                  background: grad,
                  color: '#fff', fontSize: 16, fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: `0 4px 14px rgba(20,60,120,0.2)`,
                  letterSpacing: 0.4,
                }}
              >{isCurrentPlan && plan.isPremium ? '🔄 הארכת המסלול' : '🛒 רכישת חבילה'}</button>
              )}
            </div>
          </div>
        )
      })}

      {/* ── Section: חבילות התראות ── */}
      {alertPackages.length > 0 && (
        <>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14, marginTop: 8, color: 'var(--text)' }}>
            🔔 חבילת התראות יד2
          </div>
          {alertPackages.map(pkg => {
            const qty         = getQty(pkg.id)
            const maxQty      = 8
            const totalPrice  = pkg.price * qty
            const alertAccent = '#0066d6'
            const alertGrad   = 'var(--grad-primary)'
            return (
              <div key={pkg.id} style={{
                borderRadius: 20, overflow: 'hidden', marginBottom: 22,
                boxShadow: '0 4px 18px rgba(20,60,120,0.08), 0 0 0 1px rgba(0,100,200,0.18)',
                background: 'var(--bg2)',
              }}>
                {/* Hero */}
                <div style={{
                  width: '100%', height: 150, background: alertGrad,
                  display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center', gap: 6, position: 'relative',
                }}>
                  <span style={{ fontSize: 52, lineHeight: 1 }}>🔔</span>
                  <span style={{ color: '#fff', fontSize: 13, fontWeight: 600 }}>
                    התראות על מודעות חדשות ביד2
                  </span>
                  <div style={{
                    position: 'absolute', inset: 0,
                    background: 'linear-gradient(to top, rgba(0,0,0,0.65) 0%, transparent 55%)',
                    display: 'flex', alignItems: 'flex-end', padding: '12px 14px',
                  }}>
                    <span style={{
                      fontSize: 13, fontWeight: 400, padding: '4px 12px',
                      background: alertAccent, color: '#fff',
                      borderRadius: 20, whiteSpace: 'nowrap',
                    }}>🔔 {pkg.label}</span>
                  </div>
                </div>

                {/* Chips */}
                <div style={{ display: 'flex', gap: 7, padding: '14px 14px 10px', flexWrap: 'wrap' }}>
                  <Chip accent={alertAccent}>🔔 {qty} התראה{qty > 1 ? 'ות' : ''} נוספת</Chip>
                  {(pkg.chips?.length
                    ? pkg.chips
                    : ['💳 חד-פעמי', '🔓 ללא תפוגה']
                  ).map((c, i) => <Chip key={i} accent={alertAccent}>{c}</Chip>)}
                </div>

                <div style={{ height: 1, background: 'rgba(0,100,200,0.12)', margin: '0 14px' }} />

                {/* Description */}
                <div style={{ padding: '12px 16px 8px', fontSize: 12, color: 'var(--hint)', lineHeight: 1.7 }}>
                  {pkg.features?.length > 0
                    ? pkg.features.map((f, i) => (
                        <div key={i} style={{ color: f.included !== false ? 'var(--hint)' : '#c5303066' }}>
                          {f.included !== false ? '✅' : '✗'} {f.text}
                        </div>
                      ))
                    : <>
                        <div>✅ התראה בטלגרם על כל מודעה חדשה ביד2 עבור הרכב שבחרת</div>
                        <div>✅ ניהול מעקבים מתוך הדוח</div>
                        <div>✅ עד 10 מעקבים פעילים בסה"כ (2 בסיסיות + עד 8 נרכשות)</div>
                      </>
                  }
                </div>

                <div style={{ height: 1, background: 'rgba(0,100,200,0.12)', margin: '0 14px' }} />

                {/* Quantity */}
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '12px 16px',
                }}>
                  <span style={{ fontSize: 13, color: 'var(--hint)' }}>כמות התראות</span>
                  <div style={{ display: 'flex', alignItems: 'center',
                    background: 'var(--bg)', borderRadius: 12, overflow: 'hidden' }}>
                    <button onClick={() => setQty(pkg.id, qty - 1, maxQty)} aria-label="הפחת כמות" disabled={qty <= 1} style={{
                      width: 44, height: 40, border: 'none', background: 'transparent',
                      fontSize: 22, cursor: qty <= 1 ? 'default' : 'pointer',
                      color: qty <= 1 ? 'var(--hint)' : alertAccent, fontWeight: 700,
                    }}>−</button>
                    <span style={{ width: 34, textAlign: 'center', fontWeight: 800, fontSize: 16 }} role="status" aria-label={`כמות ${qty}`}>{qty}</span>
                    <button onClick={() => setQty(pkg.id, qty + 1, maxQty)} aria-label="הוסף כמות" disabled={qty >= maxQty} style={{
                      width: 44, height: 40, border: 'none', background: 'transparent',
                      fontSize: 22, cursor: qty >= maxQty ? 'default' : 'pointer',
                      color: qty >= maxQty ? 'var(--hint)' : alertAccent, fontWeight: 700,
                    }}>+</button>
                  </div>
                  <span style={{ fontSize: 13, color: 'var(--hint)' }}>
                    מקסימום <strong style={{ color: 'var(--text)' }}>{maxQty}</strong>
                  </span>
                </div>

                {/* Price + CTA */}
                <div style={{ padding: '10px 14px 16px' }}>
                  <div style={{
                    display: 'flex', alignItems: 'baseline', justifyContent: 'center',
                    gap: 6, marginBottom: 12,
                  }}>
                    <span style={{ fontSize: 40, fontWeight: 900, color: alertAccent, lineHeight: 1 }}>
                      ₪{totalPrice}
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--hint)' }}>
                      ({qty} × ₪{pkg.price} לכל התראה)
                    </span>
                  </div>
                  <button
                    onClick={() => handleSelect({ ...pkg, _qty: qty })}
                    style={{
                      width: '100%', padding: '14px 0', border: 'none', borderRadius: 14,
                      background: alertGrad, color: '#fff', fontSize: 16, fontWeight: 700,
                      cursor: 'pointer', boxShadow: '0 4px 14px rgba(20,60,120,0.2)', letterSpacing: 0.4,
                    }}
                  >🔔 רכישת חבילת התראות</button>
                </div>
              </div>
            )
          })}
        </>
      )}

      {/* Nav buttons */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
        <button className="btn btn-secondary" style={{ marginTop: 0 }} onClick={onSupport}>
          🎫 תמיכה
        </button>
        <button className="btn btn-secondary" style={{ marginTop: 0 }} onClick={onReferral}>
          🤝 הפנה חבר
        </button>
      </div>

      <div style={{ textAlign: 'center', marginTop: 16 }}>
        <button
          onClick={onPrivacy}
          style={{ background: 'none', border: 'none', color: 'var(--hint)', fontSize: 12, cursor: 'pointer', textDecoration: 'underline', padding: '12px 8px', minHeight: 44 }}
        >
          מדיניות פרטיות ותנאי שימוש
        </button>
      </div>
    </div>
  )
}

function Row({ icon, text }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
      <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>{icon}</span>
      <span style={{ color: 'var(--text)', lineHeight: 1.5 }}>{text}</span>
    </div>
  )
}

function Chip({ children, accent }) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, padding: '4px 10px',
      background: accent ? `${accent}18` : 'var(--bg)',
      borderRadius: 20, color: accent || 'var(--hint)',
      border: `1px solid ${accent ? `${accent}44` : 'rgba(0,100,200,0.18)'}`,
      whiteSpace: 'nowrap',
    }}>{children}</span>
  )
}
