import { useState, useEffect } from 'react'
import BackButton from '../components/BackButton.jsx'
import { fetchProducts } from '../api.js'
import { safeDescriptionHtml } from '../utils/safeHtml.js'

export default function PackagesPage({ packages, user, onSelect, onPrivacy, onSupport, onReferral, onBack }) {
  const [quantities, setQuantities] = useState({})
  const [products, setProducts] = useState([])
  function getQty(id) { return quantities[id] ?? 1 }
  function setQty(id, val, max = 10) {
    setQuantities(q => ({ ...q, [id]: Math.max(1, Math.min(max, val)) }))
  }

  useEffect(() => { fetchProducts().then(setProducts).catch(() => setProducts([])) }, [])

  function handleSelect(pkg) { onSelect(pkg) }
  function handleSelectProduct(p) { onSelect({ ...p, label: p.name, _isProduct: true }) }

  const isFreeUser = user && !user.is_subscriber
  const subLabel   = user?.subscription_label || null

  const freePackage    = packages.find(p => p.searches === 0 && (p.package_type ?? 'searches') === 'searches')
  const alertPackages  = packages.filter(p => p.package_type === 'alerts')
  const paidPackages   = packages.filter(p => p.searches !== 0 && (p.package_type ?? 'searches') === 'searches')

  return (
    <div className="page" style={{ paddingBottom: 16 }}>
      {onBack && <BackButton onClick={onBack} />}
      <div className="page-title">🛒 החנות</div>

      {user && (
        <div className="card" style={{ marginBottom: 16 }}>
          <span style={{ fontSize: 14, color: 'var(--hint)' }}>
            שלום {user.first_name} · נותרו לך{' '}
            <strong>{user.searches_left === -1 ? '∞' : user.searches_left}</strong> חיפושים
            {user.is_subscriber && (
              <span style={{
                marginRight: 8, fontSize: 11, fontWeight: 400,
                background: 'linear-gradient(135deg,#1e40af,#0ea5e9)',
                color: '#000', borderRadius: 20, padding: '2px 9px',
              }}>{user.subscription_label || 'מנוי'}</span>
            )}
          </span>
        </div>
      )}

      {/* What is a subscription */}
      <div style={{
        background: 'linear-gradient(135deg,#7928ca18,#5a1e9908)',
        border: '1px solid #7928ca33',
        borderRadius: 16, padding: '16px 18px', marginBottom: 20,
      }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10, color: '#a855f7' }}>
          ⭐ מה זה חבילת חיפושים CarInfo?
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 9, fontSize: 13 }}>
          <Row icon="🔍" text="מנוי מקנה לך סל חיפושים לשימוש בקצב שלך — ללא הגבלת זמן לניצול היתרה" />
          <Row icon="💰" text="גישה לנתונים המיועדים למנויים בלבד — ככל שיתווספו תכונות נוספות בעתיד, תיהנה מהן אוטומטית" />
          <Row icon="💳" text="תשלום חד-פעמי בלבד — אין חיוב חוזר, אין מנוי אוטומטי, אין הפתעות" />
          <Row icon="🔓" text="תוקף המנוי נשמר כל עוד יש לך יתרת חיפושים — יסתיים עם ניצול מלא" />
          <Row icon="➕" text='ניתן לרכוש כמה פעמים שרוצים ולצבור חיפושים — לחץ "+" לכמות מרובה' />
        </div>

        <div style={{
          marginTop: 14, padding: '10px 14px',
          background: 'rgba(56,161,105,0.12)', borderRadius: 10,
          fontSize: 12, color: '#38a169', fontWeight: 600,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span style={{ fontSize: 16 }}>✅</span>
          <span>כל רכישה מוכנסת לחשבונך תוך שניות לאחר השלמת התשלום</span>
        </div>
      </div>

      {/* Free searches CTA */}
      <button
        onClick={onReferral}
        style={{
          display: 'flex', alignItems: 'center', gap: 14, width: '100%',
          background: 'linear-gradient(135deg, #38a169 0%, #276749 100%)',
          border: 'none', borderRadius: 16, padding: '14px 18px',
          marginBottom: 20, cursor: 'pointer', textAlign: 'right',
        }}
      >
        <span style={{ fontSize: 36, flexShrink: 0 }}>🎁</span>
        <div>
          <div style={{ color: '#fff', fontWeight: 700, fontSize: 16, marginBottom: 3 }}>
            רוצה חיפושים בחינם?
          </div>
          <div style={{ color: 'rgba(255,255,255,0.82)', fontSize: 13 }}>
            הפנה חברים וקבל חיפושים על כל הצטרפות ←
          </div>
          <div style={{ color: 'rgba(255,255,255,0.55)', fontSize: 11, marginTop: 3 }}>
            * חיפושים אלו אינם כוללים גישה לתכונות המיועדות למנויים
          </div>
        </div>
      </button>

      {/* ── Section: מוצרים דיגיטליים ── */}
      {products.length > 0 && (
        <>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14, color: 'var(--text)' }}>
            🛍️ מוצרים דיגיטליים
          </div>
          {products.map(p => {
            const accent = '#f59e0b'
            const grad   = 'linear-gradient(135deg,#92400e,#f59e0b)'
            return (
              <div key={p.id} style={{
                borderRadius: 20, overflow: 'hidden', marginBottom: 22, position: 'relative',
                boxShadow: '0 6px 28px rgba(0,0,0,0.18), 0 0 0 1px rgba(255,255,255,0.07)',
                background: 'var(--bg2)', opacity: p.in_stock ? 1 : 0.6,
              }}>
                {!p.in_stock && (
                  <div style={{
                    position: 'absolute', top: 10, left: 10, zIndex: 1,
                    background: '#e53e3e', color: '#fff', fontSize: 11, fontWeight: 700,
                    borderRadius: 20, padding: '3px 10px',
                  }}>אזל המלאי</div>
                )}
                <div style={{ position: 'relative', height: p.image_url ? 170 : 150 }}>
                  {p.image_url
                    ? <img src={p.image_url} alt={p.name}
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
                      background: accent, color: '#000', borderRadius: 20, whiteSpace: 'nowrap',
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
                    <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0 14px' }} />
                    <div
                      style={{ padding: '12px 16px', fontSize: 13, color: 'var(--hint)', lineHeight: 1.7 }}
                      dangerouslySetInnerHTML={{ __html: safeDescriptionHtml(p.description) }}
                    />
                  </>
                )}

                <div style={{ padding: '10px 14px 16px' }}>
                  <div style={{
                    display: 'flex', alignItems: 'baseline', justifyContent: 'center',
                    gap: 6, marginBottom: 12,
                  }}>
                    <span style={{ fontSize: 40, fontWeight: 900, color: accent, lineHeight: 1 }}>
                      ₪{p.price}
                    </span>
                  </div>
                  <button
                    onClick={() => handleSelectProduct(p)}
                    disabled={!p.in_stock}
                    style={{
                      width: '100%', padding: '14px 0', border: 'none', borderRadius: 14,
                      background: p.in_stock ? grad : 'var(--bg)',
                      color: p.in_stock ? '#fff' : 'var(--hint)', fontSize: 16, fontWeight: 700,
                      cursor: p.in_stock ? 'pointer' : 'default',
                      boxShadow: p.in_stock ? '0 4px 14px rgba(0,0,0,0.25)' : 'none',
                      letterSpacing: 0.4,
                    }}
                  >{p.in_stock ? '🛍️ רכישה' : 'אזל המלאי'}</button>
                </div>
              </div>
            )
          })}
        </>
      )}

      {/* ── FREE card ── */}
      {(() => {
        const freeAccent = '#52b788'
        const freeGrad   = 'linear-gradient(135deg,#1b4332,#2d6a4f)'
        const searchesLeft = user?.searches_left ?? 0
        return (
          <div style={{
            borderRadius: 20, overflow: 'hidden', marginBottom: 22,
            boxShadow: isFreeUser
              ? '0 6px 28px rgba(0,0,0,0.18), 0 0 0 2px #4caf50'
              : '0 6px 28px rgba(0,0,0,0.18), 0 0 0 1px rgba(255,255,255,0.07)',
            background: 'var(--bg2)',
          }}>
            {isFreeUser && (
              <div style={{
                background: 'linear-gradient(90deg,#4caf50,#2e7d32)',
                padding: '6px 14px', fontSize: 12, fontWeight: 700, color: '#fff',
                display: 'flex', alignItems: 'center', gap: 6,
              }}>✓ המנוי שלך כרגע</div>
            )}

            {/* Hero */}
            <div style={{
              position: 'relative', height: freePackage?.image_url ? 170 : 150,
            }}>
              {freePackage?.image_url
                ? <img src={freePackage.image_url} alt="FREE"
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
                        <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13, fontWeight: 600 }}>
                          חיפושים נותרו
                        </span>
                      </>
                    ) : (
                      <>
                        <span style={{ fontSize: 52, lineHeight: 1 }}>🆓</span>
                        <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13, fontWeight: 600 }}>
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
                  background: freeAccent, color: '#000', borderRadius: 20, whiteSpace: 'nowrap',
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

            <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0 14px' }} />

            {/* Info — dynamic from DB, fallback to hardcoded */}
            <div style={{ padding: '12px 16px', fontSize: 13, lineHeight: 1.9 }}>
              {(freePackage?.features?.length
                ? freePackage.features
                : [
                    { text: 'נתוני רכב בסיסיים — שנה, דגם, בעלות, טסט, ק״מ', included: true },
                    { text: 'היסטוריית חיפושים אישית', included: true },
                    { text: 'מחיר שוק Yad2', included: false },
                    { text: 'הורדת דוח PDF מפורט', included: false },
                    { text: 'העתקת דוח לשיתוף', included: false },
                    { text: 'הערות אישיות לכל רכב', included: false },
                  ]
              ).map((f, i) => {
                const text = typeof f === 'string' ? f : f.text
                const included = typeof f === 'string' ? true : f.included
                return (
                  <div key={i} style={{ color: included ? 'var(--hint)' : '#e53e3e', opacity: included ? 1 : 0.75 }}>
                    {included ? '✅' : '✗'} {text}
                  </div>
                )
              })}
            </div>

            {/* CTA */}
            <div style={{ padding: '10px 14px 16px' }}>
              <button
                onClick={onReferral}
                style={{
                  width: '100%', padding: '14px 0', border: 'none', borderRadius: 14,
                  background: freeGrad, color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer',
                  boxShadow: '0 4px 14px rgba(0,0,0,0.25)',
                }}
              >🤝 קבל עוד חיפושים חינם</button>
            </div>
          </div>
        )
      })()}

      {/* ── Section header: חבילות חיפושים ── */}
      <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 14, color: 'var(--text)' }}>
        🔍 חבילות חיפושים
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

        const grad   = 'linear-gradient(135deg,#1e40af,#0ea5e9)'
        const accent = '#38bdf8'

        const isCurrentPlan = user?.is_subscriber && subLabel &&
          (subLabel === pkg.label || subLabel.startsWith(pkg.label + ' ×'))

        return (
          <div key={pkg.id} style={{
            borderRadius: 20, overflow: 'hidden', marginBottom: 22,
            boxShadow: isCurrentPlan
              ? '0 6px 28px rgba(0,0,0,0.18), 0 0 0 2px #4caf50'
              : '0 6px 28px rgba(0,0,0,0.18), 0 0 0 1px rgba(255,255,255,0.07)',
            background: 'var(--bg2)',
          }}>

          {isCurrentPlan && (
            <div style={{
              background: 'linear-gradient(90deg,#4caf50,#2e7d32)',
              padding: '6px 14px', fontSize: 12, fontWeight: 700, color: '#fff',
              display: 'flex', alignItems: 'center', gap: 6,
            }}>✓ המנוי שלך כרגע</div>
          )}

            {/* ── Hero ── */}
            <div style={{ position: 'relative', height: pkg.image_url ? 170 : 150 }}>
              {pkg.image_url
                ? <img src={pkg.image_url} alt={pkg.label}
                    style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                : <div style={{ width: '100%', height: '100%', background: grad,
                    display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                    <span style={{ fontSize: 52, lineHeight: 1 }}>{isUnlimited ? '♾️' : '⭐'}</span>
                    <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13, fontWeight: 600 }}>
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
                  background: accent, color: '#000',
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

            <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0 14px' }} />

            {/* ── Features ── */}
            <div style={{ padding: '12px 16px', fontSize: 13, lineHeight: 1.9 }}>
              {(pkg.features?.length
                ? pkg.features
                : [
                    { text: 'מחיר שוק Yad2 — השוואת מחירים עדכנית', included: true },
                    { text: 'הורדת דוח PDF מפורט', included: true },
                    { text: 'העתקת דוח לשיתוף', included: true },
                    { text: 'הערות אישיות לכל רכב — נשמרות ומופיעות בדוח', included: true },
                    { text: 'היסטוריית חיפושים אישית', included: true },
                    { text: 'גישה לכל תכונות המנוי הקיימות והעתידיות', included: true },
                  ]
              ).map((f, i) => {
                const text = typeof f === 'string' ? f : f.text
                const included = typeof f === 'string' ? true : f.included
                return (
                  <div key={i} style={{ color: included ? 'var(--hint)' : '#e53e3e', opacity: included ? 1 : 0.75 }}>
                    {included ? '✅' : '✗'} {text}
                  </div>
                )
              })}
            </div>

            <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0 14px' }} />
            {!isUnlimited && (
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '12px 16px',
              }}>
                <span style={{ fontSize: 13, color: 'var(--hint)' }}>כמות</span>
                <div style={{ display: 'flex', alignItems: 'center',
                  background: 'var(--bg)', borderRadius: 12, overflow: 'hidden' }}>
                  <button onClick={() => setQty(pkg.id, qty - 1)} disabled={qty <= 1} style={{
                    width: 44, height: 40, border: 'none', background: 'transparent',
                    fontSize: 22, cursor: qty <= 1 ? 'default' : 'pointer',
                    color: qty <= 1 ? 'var(--hint)' : accent, fontWeight: 700,
                  }}>−</button>
                  <span style={{ width: 34, textAlign: 'center', fontWeight: 800, fontSize: 16 }}>{qty}</span>
                  <button onClick={() => setQty(pkg.id, qty + 1)} disabled={qty >= 10} style={{
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
              <button
                onClick={() => handleSelect(pkg)}
                style={{
                  width: '100%', padding: '14px 0', border: 'none', borderRadius: 14,
                  background: grad,
                  color: '#fff', fontSize: 16, fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: `0 4px 14px rgba(0,0,0,0.25)`,
                  letterSpacing: 0.4,
                }}
              >🛒 רכישת חבילה</button>
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
            const alertAccent = '#8b5cf6'
            const alertGrad   = 'linear-gradient(135deg,#4c1d95,#7c3aed)'
            return (
              <div key={pkg.id} style={{
                borderRadius: 20, overflow: 'hidden', marginBottom: 22,
                boxShadow: '0 6px 28px rgba(0,0,0,0.18), 0 0 0 1px rgba(255,255,255,0.07)',
                background: 'var(--bg2)',
              }}>
                {/* Hero */}
                <div style={{
                  width: '100%', height: 150, background: alertGrad,
                  display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center', gap: 6, position: 'relative',
                }}>
                  <span style={{ fontSize: 52, lineHeight: 1 }}>🔔</span>
                  <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13, fontWeight: 600 }}>
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

                <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0 14px' }} />

                {/* Description */}
                <div style={{ padding: '12px 16px 8px', fontSize: 12, color: 'var(--hint)', lineHeight: 1.7 }}>
                  {pkg.features?.length > 0
                    ? pkg.features.map((f, i) => (
                        <div key={i} style={{ color: f.included !== false ? 'var(--hint)' : '#e53e3e66' }}>
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

                <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0 14px' }} />

                {/* Quantity */}
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '12px 16px',
                }}>
                  <span style={{ fontSize: 13, color: 'var(--hint)' }}>כמות התראות</span>
                  <div style={{ display: 'flex', alignItems: 'center',
                    background: 'var(--bg)', borderRadius: 12, overflow: 'hidden' }}>
                    <button onClick={() => setQty(pkg.id, qty - 1, maxQty)} disabled={qty <= 1} style={{
                      width: 44, height: 40, border: 'none', background: 'transparent',
                      fontSize: 22, cursor: qty <= 1 ? 'default' : 'pointer',
                      color: qty <= 1 ? 'var(--hint)' : alertAccent, fontWeight: 700,
                    }}>−</button>
                    <span style={{ width: 34, textAlign: 'center', fontWeight: 800, fontSize: 16 }}>{qty}</span>
                    <button onClick={() => setQty(pkg.id, qty + 1, maxQty)} disabled={qty >= maxQty} style={{
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
                      cursor: 'pointer', boxShadow: '0 4px 14px rgba(0,0,0,0.25)', letterSpacing: 0.4,
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
          style={{ background: 'none', border: 'none', color: 'var(--hint)', fontSize: 12, cursor: 'pointer', textDecoration: 'underline' }}
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
      border: `1px solid ${accent ? `${accent}44` : 'rgba(255,255,255,0.07)'}`,
      whiteSpace: 'nowrap',
    }}>{children}</span>
  )
}
